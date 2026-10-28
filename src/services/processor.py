import asyncio
import logging
from contextlib import suppress

from src.media.transcriber import Transcriber
from src.domain.errors import ProcessingError, TaskNotFoundError
from src.domain.models import ErrorCode, TaskError, TaskStage, TaskStatus
from src.media.audio import extract_audio
from src.repositories.base import TaskRepository
from src.settings import now
from src.storage.files import TaskFiles

logger = logging.getLogger(__name__)


class MidiTaskProcessor:
    """Runs the full pipeline for one task and keeps its status up to date."""

    def __init__(
        self,
        repository: TaskRepository,
        files: TaskFiles,
        transcriber: Transcriber,
        ffmpeg_timeout: float,
    ) -> None:
        self._repo = repository
        self._files = files
        self._transcriber = transcriber
        self._ffmpeg_timeout = ffmpeg_timeout

    async def process(self, task_id: str) -> None:
        task = await self._repo.get(task_id)
        if task is None:
            logger.warning("Task %s not found, skipping", task_id)
            return

        try:
            await self._repo.update(
                task_id,
                status=TaskStatus.PROCESSING,
                stage=TaskStage.EXTRACTING_AUDIO,
                started_at=now(),
            )
            await extract_audio(
                self._files.input_path(task_id),
                self._files.audio_path(task_id),
                self._ffmpeg_timeout,
            )

            await self._repo.update(task_id, stage=TaskStage.TRANSCRIBING)
            try:
                await self._transcriber.transcribe(
                    self._files.audio_path(task_id),
                    self._files.result_path(task_id),
                )
            except Exception as exc:
                logger.exception("Transcription failed for task %s", task_id)
                raise ProcessingError(
                    ErrorCode.TRANSCRIPTION_FAILED, "Failed to transcribe audio to MIDI"
                ) from exc

            await self._repo.update(
                task_id,
                status=TaskStatus.COMPLETED,
                stage=None,
                finished_at=now(),
            )
            logger.info("Task %s completed", task_id)

        except ProcessingError as exc:
            await self._fail(task_id, TaskError(code=exc.code, message=exc.message))
        except TaskNotFoundError:
            logger.warning("Task %s disappeared during processing", task_id)
        except Exception:
            logger.exception("Unexpected error in task %s", task_id)
            await self._fail(
                task_id,
                TaskError(code=ErrorCode.INTERNAL_ERROR, message="Internal error"),
            )
        finally:
            # the uploaded video and the wav are no longer needed
            await asyncio.to_thread(self._files.remove_intermediate, task_id)

    async def _fail(self, task_id: str, error: TaskError) -> None:
        logger.error(
            "Task %s failed: %s - %s", task_id, error.code.value, error.message
        )
        with suppress(TaskNotFoundError):
            await self._repo.update(
                task_id,
                status=TaskStatus.FAILED,
                stage=None,
                finished_at=now(),
                error=error,
            )
