import asyncio
import logging
import os
import shutil
import subprocess
from tempfile import NamedTemporaryFile
from typing import IO

import basic_pitch.inference
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from concurrent.futures import ProcessPoolExecutor

if shutil.which("ffmpeg") is None:
    msg = "ffmpeg not found in PATH"
    raise RuntimeError(msg)

CHUNK_SIZE = 32 * 1024 * 1024  # 32 MiB

ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/x-msvideo",
    "video/quicktime",
    "video/x-matroska",
    "video/webm",
    "video/x-flv",
    "video/x-ms-wmv",
    "video/mpeg",
    "video/3gpp",
}


logger = logging.getLogger(__name__)

app = FastAPI()


def ffmpeg_cmd(input_filename: str, out_media_type: str) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        input_filename,
        "-map",
        "a",
        "-c:a",
        "copy",
        "-f",
        out_media_type,
        "-",
    ]


def safe_unlink(filepath: str, attempts: int = 1):
    for attempt in range(1, attempts + 1):
        try:
            logger.debug("Trying to unlink file %s | attempt %d", filepath, attempt)
            os.unlink(filepath)
        except OSError:
            logger.warning(
                "Error during file %s unlink | attempt %d", filepath, attempt
            )
            continue
        else:
            logger.debug("Successfully unlink file %s", filepath)
            return
    else:
        logger.error("Error to unlink file %s in %d attempts", filepath, attempts)


async def save_input_file(file: UploadFile, to: IO[bytes]) -> None:
    total = 0
    while chunk := await file.read(CHUNK_SIZE):
        total += len(chunk)
        await asyncio.to_thread(to.write, chunk)

    if total == 0:
        msg = "Empty file"
        logger.error(msg)
        raise HTTPException(400, msg)

    logger.info("%d bytes read", total)


async def extract_audio(file: IO[bytes], to: IO[bytes]):
    logger.info(
        "Staring ffmpeg process with input file %s, out media type: %s",
        file.name,
        "ogg",
    )
    ffmpeg = await asyncio.to_thread(
        lambda: subprocess.Popen(
            ffmpeg_cmd(file.name, "ogg"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    )

    if ffmpeg.stdout is None:
        logger.error("ffmpeg.stdout is None")
        raise HTTPException(500)

    if ffmpeg.stderr is None:
        logger.error("ffmpeg.stderr is None")
        raise HTTPException(500)

    ffmpeg_stderr_task = asyncio.create_task(asyncio.to_thread(ffmpeg.stderr.read))

    logger.debug("Writing result to %s", to.name)
    while chunk := await asyncio.to_thread(ffmpeg.stdout.read, CHUNK_SIZE):
        await asyncio.to_thread(to.write, chunk)

    try:
        await asyncio.to_thread(ffmpeg.wait, timeout=10)
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg process timed out")
        await asyncio.to_thread(ffmpeg.kill)
        await asyncio.to_thread(ffmpeg.wait)
    else:
        logger.info("ffmpeg process exit with code %d", ffmpeg.returncode)

    if ffmpeg.returncode != 0:
        error = await ffmpeg_stderr_task
        msg = error.decode("utf-8", errors="ignore").strip()
        logger.error(msg)
        raise HTTPException(500, "Internal ffmpeg error")


@app.post("/upload")
async def upload_video(file: UploadFile):
    if not file.content_type:
        msg = "Unable to check content type"
        logger.error(msg)
        raise HTTPException(400, msg)

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        msg = "Invalid content type"
        logger.error(msg)
        raise HTTPException(400, msg)

    tmp_input_file: IO[bytes] | None = None
    tmp_audio_file: IO[bytes] | None = None
    tmp_midi_file: IO[bytes] | None = None
    try:
        with await asyncio.to_thread(
            lambda: NamedTemporaryFile(mode="wb", delete=False),
        ) as tmp_input_file:
            logger.debug("Writing to temp file %s", tmp_input_file.name)
            await save_input_file(file, tmp_input_file)

        with await asyncio.to_thread(
            lambda: NamedTemporaryFile(mode="wb", delete=False),
        ) as tmp_audio_file:
            await extract_audio(tmp_input_file, tmp_audio_file)

        with ProcessPoolExecutor() as executor:
            loop = asyncio.get_running_loop()
            _, midi_data, _ = await loop.run_in_executor(
                executor,
                basic_pitch.inference.predict,
                tmp_audio_file.name,
            )

        with await asyncio.to_thread(
            lambda: NamedTemporaryFile("wb", delete=False)
        ) as tmp_midi_file:
            await asyncio.to_thread(midi_data.write, tmp_midi_file)

        return FileResponse(
            tmp_midi_file.name,
            media_type="audio/midi",
            background=BackgroundTask(
                lambda attempts: (
                    safe_unlink(tmp_input_file.name, attempts),
                    safe_unlink(tmp_audio_file.name, attempts),
                    safe_unlink(tmp_midi_file.name, attempts),
                ),
                10,
            ),
        )

    except Exception:
        if tmp_input_file:
            safe_unlink(tmp_input_file.name)
        if tmp_audio_file:
            safe_unlink(tmp_audio_file.name)
        if tmp_midi_file:
            safe_unlink(tmp_midi_file.name)
        raise


if __name__ == "__main__":
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger.addHandler(handler)
    handler.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)
    handler.setLevel(logging.DEBUG)

    uvicorn.run(app)
