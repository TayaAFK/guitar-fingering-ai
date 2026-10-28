import asyncio
import logging

from src.queues.base import TaskQueue
from src.services.processor import MidiTaskProcessor

logger = logging.getLogger(__name__)


class Worker:
    """Pulls task ids from the queue and processes them (`concurrency` at a time)."""

    def __init__(
        self, queue: TaskQueue, processor: MidiTaskProcessor, concurrency: int
    ) -> None:
        self._queue = queue
        self._processor = processor
        self._concurrency = concurrency

    async def run(self) -> None:
        await asyncio.gather(*(self._loop() for _ in range(self._concurrency)))

    async def _loop(self) -> None:
        while True:
            task_id = await self._queue.dequeue()
            try:
                await self._processor.process(task_id)
            except Exception:  # the worker must never die
                logger.exception("Worker crashed on task %s", task_id)
