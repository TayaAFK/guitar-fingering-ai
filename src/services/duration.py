import asyncio
from contextlib import suppress
import logging
from pathlib import Path

from src.domain.errors import ProcessingError
from src.domain.models import ErrorCode

logger = logging.getLogger(__name__)


async def get_duration(file: Path) -> float:
    ffprobe = await asyncio.create_subprocess_exec(
        *[
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(file),
                "-show_entries",
                "format=duration",
                "-of",
                "default=nokey=1:noprint_wrappers=1",
        ],
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        ffprobe_stdout, ffprobe_stderr = await asyncio.wait_for(ffprobe.communicate(), None)
    except asyncio.TimeoutError:
        raise ProcessingError(ErrorCode.TIMEOUT, "FFprobe inspection took too long and was aborted")
    finally:
        if ffprobe.returncode is None:
            with suppress(ProcessLookupError):
                ffprobe.kill()
            await ffprobe.wait()

    if ffprobe.returncode == 0:
        try:
            duration = float(ffprobe_stdout.strip().decode())
        except Exception:
            logger.exception("Duration converting to float ends with error")
            raise ProcessingError(ErrorCode.INTERNAL_ERROR, "Invalid duration data")
        return duration

    error = ffprobe_stderr.decode("utf-8", errors="ignore").strip()
    logger.error("ffprobe exited with code %d: %s", ffprobe.returncode, error)
    raise ProcessingError(ErrorCode.INTERNAL_ERROR, "Unable to inspect video duration")
