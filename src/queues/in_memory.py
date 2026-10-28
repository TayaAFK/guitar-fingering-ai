import asyncio

from src.domain.errors import QueueFullError
from src.queues.base import TaskQueue


class InMemoryTaskQueue(TaskQueue):
    def __init__(self, max_size: int = 0) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=max_size)

    async def enqueue(self, task_id: str) -> None:
        try:
            self._queue.put_nowait(task_id)
        except asyncio.QueueFull as exc:
            raise QueueFullError from exc

    async def dequeue(self) -> str:
        return await self._queue.get()
