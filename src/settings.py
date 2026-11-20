import os
from datetime import datetime, timezone
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    upload_bytes_limit: int = 100 * 1024 * 1024  # 0 = unlimited
    work_dir: Path | None = None  # None = private temp dir, removed on shutdown
    workers: int = 2  # concurrently processed tasks
    queue_max_size: int = 100  # tasks waiting in the queue
    result_ttl: float = 3600.0  # how long finished tasks are kept
    cleanup_interval: float = 60.0  # seconds
    ffmpeg_timeout: float = 900.0  # seconds
    video_duration_limit: float = 600.0  # seconds


def now() -> datetime:
    return datetime.now(timezone.utc)
