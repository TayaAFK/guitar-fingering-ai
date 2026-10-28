import asyncio
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


async def get_duration(file: Path) -> float:
    ffprobe = await asyncio.to_thread(
        lambda: subprocess.Popen(
            [
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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ),
    )

    assert ffprobe.stdout
    assert ffprobe.stderr

    duration = float((await asyncio.to_thread(ffprobe.stdout.read)).decode())
    error = await asyncio.to_thread(ffprobe.stderr.read)

    await asyncio.to_thread(ffprobe.wait)

    if ffprobe.returncode != 0:
        msg = (
            f"Internal ffprobe error: {error.decode('utf-8', errors='ignore').strip()}"
        )
        logger.error(msg)
        raise RuntimeError(msg)

    return duration
