import asyncio
import logging
from datetime import timedelta

from src.settings import now
from src.repositories.base import TaskRepository
from src.storage.files import TaskFiles

logger = logging.getLogger(__name__)


class ExpiredTaskCleaner:
    def __init__(
        self,
        repository: TaskRepository,
        files: TaskFiles,
        ttl: timedelta,
        interval: float,
    ) -> None:
        self._repo = repository
        self._files = files
        self._ttl = ttl
        self._interval = interval

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                await self.sweep()
            except Exception:
                logger.exception("Cleanup failed")

    async def sweep(self) -> None:
        for task in await self._repo.list_finished_before(now() - self._ttl):
            await self._repo.delete(task.id)
            await asyncio.to_thread(self._files.remove, task.id)
            logger.info("Task %s expired and was removed", task.id)
