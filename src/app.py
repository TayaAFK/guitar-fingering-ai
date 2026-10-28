import asyncio
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from src.settings import Settings
from src.media.transcriber import BasicPitchTranscriber
from src.queues.in_memory import InMemoryTaskQueue
from src.repositories.in_memory import InMemoryTaskRepository
from src.services.cleaner import ExpiredTaskCleaner
from src.services.processor import MidiTaskProcessor
from src.services.task_service import TaskService
from src.services.worker import Worker
from src.storage.files import TaskFiles
from src.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    if shutil.which("ffmpeg") is None:
        msg = "ffmpeg not found in PATH"
        raise RuntimeError(msg)

    settings = Settings.from_env()
    owns_work_dir = settings.work_dir is None
    work_dir = settings.work_dir or Path(tempfile.mkdtemp(prefix="video2midi-"))
    work_dir.mkdir(parents=True, exist_ok=True)

    repository = InMemoryTaskRepository()
    queue = InMemoryTaskQueue(settings.queue_max_size)
    files = TaskFiles(work_dir)
    transcriber = BasicPitchTranscriber(max_workers=settings.workers)
    processor = MidiTaskProcessor(
        repository, files, transcriber, settings.ffmpeg_timeout
    )

    app.state.service = TaskService(
        repository, queue, files, settings.upload_bytes_limit, settings.video_duration_limit
    )

    background = [
        asyncio.create_task(
            Worker(queue, processor, settings.workers).run(), name="worker"
        ),
        asyncio.create_task(
            ExpiredTaskCleaner(
                repository, files, settings.result_ttl, settings.cleanup_interval
            ).run(),
            name="cleaner",
        ),
    ]
    try:
        yield
    finally:
        for t in background:
            t.cancel()
        await asyncio.gather(*background, return_exceptions=True)
        transcriber.close()
        if owns_work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    return app
