from datetime import datetime

from src.repositories.base import TaskRepository
from src.domain.models import Task
from src.domain.errors import TaskNotFoundError


class InMemoryTaskRepository(TaskRepository):
    # Methods have no `await` inside, so on a single event loop each of them
    # is atomic and no lock is required.

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    async def add(self, task: Task) -> None:
        self._tasks[task.id] = task

    async def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    async def update(self, task_id: str, **fields) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        updated = task.model_copy(update=fields)
        self._tasks[task_id] = updated
        return updated

    async def delete(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)

    async def list_finished_before(self, cutoff: datetime) -> list[Task]:
        return [
            t
            for t in self._tasks.values()
            if t.finished_at is not None and t.finished_at < cutoff
        ]
