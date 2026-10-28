from datetime import datetime

from pydantic import BaseModel

from src.domain.models import Task, TaskError, TaskStage, TaskStatus


class UploadResponse(BaseModel):
    task_id: str
    status: TaskStatus
    status_url: str
    result_url: str
    created_at: datetime


class StatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    stage: TaskStage | None
    message: str
    filename: str | None
    size_bytes: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: TaskError | None
    result_url: str | None

    @classmethod
    def from_task(cls, task: Task) -> "StatusResponse":
        return cls(
            task_id=task.id,
            status=task.status,
            stage=task.stage,
            message=describe(task),
            filename=task.filename,
            size_bytes=task.size_bytes,
            created_at=task.created_at,
            started_at=task.started_at,
            finished_at=task.finished_at,
            error=task.error,
            result_url=(
                result_url(task.id) if task.status is TaskStatus.COMPLETED else None
            ),
        )


_STAGE_MESSAGES = {
    TaskStage.EXTRACTING_AUDIO: "Extracting audio from the video",
    TaskStage.TRANSCRIBING: "Converting audio to MIDI",
}


def status_url(task_id: str) -> str:
    return f"/status/{task_id}"


def result_url(task_id: str) -> str:
    return f"/result/{task_id}"


def describe(task: Task) -> str:
    match task.status:
        case TaskStatus.QUEUED:
            return "Waiting in the queue"
        case TaskStatus.PROCESSING:
            return _STAGE_MESSAGES.get(task.stage, "Processing")  # type: ignore[arg-type]
        case TaskStatus.COMPLETED:
            return "The MIDI file is ready"
        case TaskStatus.FAILED:
            return task.error.message if task.error else "Processing failed"
