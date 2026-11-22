from abc import ABC, abstractmethod


class TaskQueue(ABC):
    """Queue of task ids. Implement for RabbitMQ / Redis / SQS / etc."""

    @abstractmethod
    async def enqueue(self, task_id: str) -> None:
        """Raise QueueFullError if the queue cannot accept more tasks."""

    @abstractmethod
    async def dequeue(self) -> str:
        """Wait for and return the next task id."""
