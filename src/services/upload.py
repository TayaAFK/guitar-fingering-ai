import asyncio
import logging
from pathlib import Path
from typing import Protocol

from src.domain.errors import EmptyUploadError, UploadTooLargeError

CHUNK_SIZE = 8192  # 8 KiB


logger = logging.getLogger(__name__)


class AsyncReader(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


async def save_upload(file: AsyncReader, path: Path, limit_bytes: int) -> int:
    total = 0
    with path.open("wb") as out:
        while chunk := await file.read(CHUNK_SIZE):
            total += len(chunk)
            if limit_bytes > 0 and total > limit_bytes:
                raise UploadTooLargeError(limit_bytes)
            await asyncio.to_thread(out.write, chunk)

    if total == 0:
        raise EmptyUploadError
    logger.info("%d bytes saved to %s", total, path)
    return total
