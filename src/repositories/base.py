from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.models import Task


class TaskRepository(ABC):
    """Task metadata storage. Implement for Redis / SQL / etc."""

    @abstractmethod
    async def add(self, task: Task) -> None: ...

    @abstractmethod
    async def get(self, task_id: str) -> Task | None: ...

    @abstractmethod
    async def update(self, task_id: str, **fields) -> Task:
        """Apply field updates, return the new snapshot. Raise TaskNotFoundError."""

    @abstractmethod
    async def delete(self, task_id: str) -> None: ...

    @abstractmethod
    async def list_finished_before(self, cutoff: datetime) -> list[Task]:
        """Completed/failed tasks with finished_at < cutoff (for TTL cleanup)."""
