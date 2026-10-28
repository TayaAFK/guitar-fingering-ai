from dataclasses import dataclass
from pathlib import Path
from datetime import timedelta, datetime, timezone
import os

@dataclass(frozen=True)
class Settings:
    upload_bytes_limit: int = 0  # 0 = unlimited
    work_dir: Path | None = None  # None = private temp dir, removed on shutdown
    workers: int = 2  # concurrently processed tasks
    queue_max_size: int = 100  # tasks waiting in the queue
    result_ttl: timedelta = timedelta(hours=1)  # how long finished tasks are kept
    cleanup_interval: float = 60.0  # seconds
    ffmpeg_timeout: float = 900.0  # seconds
    video_duration_limit: int = 0  # seconds

    @classmethod
    def from_env(cls) -> "Settings":
        work_dir = os.getenv("WORK_DIR")
        return cls(
            upload_bytes_limit=int(os.getenv("UPLOAD_BYTES_LIMIT", 0)),
            work_dir=Path(work_dir) if work_dir else None,
            workers=int(os.getenv("WORKERS", 2)),
            queue_max_size=int(os.getenv("QUEUE_MAX_SIZE", 100)),
            result_ttl=timedelta(seconds=int(os.getenv("RESULT_TTL_SECONDS", 3600))),
            cleanup_interval=float(os.getenv("CLEANUP_INTERVAL_SECONDS", 60)),
            ffmpeg_timeout=float(os.getenv("FFMPEG_TIMEOUT_SECONDS", 900)),
            video_duration_limit=int(os.getenv("VIDEO_DURATION_LIMIT", 0))
        )


def now() -> datetime:
    return datetime.now(timezone.utc)
