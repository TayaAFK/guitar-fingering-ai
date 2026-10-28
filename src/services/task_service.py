import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import UploadFile

from src.domain.errors import DurationExceedError
from src.domain.models import Task
from src.queues.base import TaskQueue
from src.repositories.base import TaskRepository
from src.services.duration import get_duration
from src.services.upload import save_upload
from src.settings import now
from src.storage.files import TaskFiles

logger = logging.getLogger(__name__)


class TaskService:
    """What the HTTP layer talks to."""

    def __init__(
        self,
        repository: TaskRepository,
        queue: TaskQueue,
        files: TaskFiles,
        upload_bytes_limit: int,
        video_duration_limit: int
    ) -> None:
        self._repo = repository
        self._queue = queue
        self._files = files
        self._upload_limit = upload_bytes_limit
        self._video_duration_limit = video_duration_limit

    async def submit(self, file: UploadFile) -> Task:
        task_id = uuid.uuid4().hex
        await asyncio.to_thread(self._files.create, task_id)
        try:
            size = await save_upload(
                file, self._files.input_path(task_id), self._upload_limit
            )

            duration = await get_duration(self._files.input_path(task_id))
            if self._video_duration_limit > 0 and duration > self._video_duration_limit:
                raise DurationExceedError(self._video_duration_limit)

            task = Task(
                id=task_id,
                filename=file.filename[:255] if file.filename else None,
                content_type=file.content_type or "",
                size_bytes=size,
                created_at=now(),
            )
            await self._repo.add(task)
            try:
                await self._queue.enqueue(task_id)
            except BaseException:
                await self._repo.delete(task_id)
                raise
        except BaseException:
            self._files.remove(task_id)
            raise
        logger.info("Task %s queued", task_id)
        return task

    async def get(self, task_id: str) -> Task | None:
        return await self._repo.get(task_id)

    def result_path(self, task_id: str) -> Path:
        return self._files.result_path(task_id)
