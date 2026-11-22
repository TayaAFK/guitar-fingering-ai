from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStage(str, Enum):
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"


class ErrorCode(str, Enum):
    INVALID_MEDIA = "invalid_media"  # file is broken / not a video
    NO_AUDIO_TRACK = "no_audio_track"  # video has no audio
    TIMEOUT = "timeout"
    AUDIO_EXTRACTION_FAILED = "audio_extraction_failed"
    TRANSCRIPTION_FAILED = "transcription_failed"
    INTERNAL_ERROR = "internal_error"


CLIENT_ERROR_CODES = {ErrorCode.INVALID_MEDIA, ErrorCode.NO_AUDIO_TRACK}


class TaskError(BaseModel):
    code: ErrorCode
    message: str


class Task(BaseModel):
    """Immutable task snapshot. Updates produce a new object (see repository)."""

    model_config = ConfigDict(frozen=True)

    id: str
    status: TaskStatus = TaskStatus.QUEUED
    stage: TaskStage | None = None
    filename: str | None = None
    content_type: str
    size_bytes: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: TaskError | None = None
