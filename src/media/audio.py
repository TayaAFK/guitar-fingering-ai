import asyncio
import logging
from contextlib import suppress
from pathlib import Path

from src.domain.errors import ProcessingError
from src.domain.models import ErrorCode

logger = logging.getLogger(__name__)


def ffmpeg_cmd(input_path: Path, output_path: Path) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:a:0",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "22050",
        "-ac",
        "1",
        "-f",
        "wav",
        str(output_path),
    ]


async def extract_audio(input_path: Path, output_path: Path, timeout: float) -> None:
    logger.info("Starting ffmpeg for %s", input_path)
    proc = await asyncio.create_subprocess_exec(
        *ffmpeg_cmd(input_path, output_path),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        raise ProcessingError(
            ErrorCode.TIMEOUT, "Audio extraction took too long and was aborted"
        ) from None
    finally:
        if proc.returncode is None:  # timeout or cancellation
            with suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()

    if proc.returncode == 0:
        return

    error = stderr.decode("utf-8", errors="ignore").strip()
    logger.error("ffmpeg exited with code %d: %s", proc.returncode, error)

    if "matches no streams" in error or "does not contain any stream" in error:
        raise ProcessingError(ErrorCode.NO_AUDIO_TRACK, "The video has no audio track")
    if "Invalid data found" in error or "moov atom not found" in error:
        raise ProcessingError(
            ErrorCode.INVALID_MEDIA, "The file is corrupted or is not a valid video"
        )
    raise ProcessingError(
        ErrorCode.AUDIO_EXTRACTION_FAILED, "Failed to extract audio from the video"
    )
