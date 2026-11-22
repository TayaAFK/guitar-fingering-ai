import asyncio
import logging
import multiprocessing
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

logger = logging.getLogger(__name__)


class Transcriber(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: Path, midi_path: Path) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


def _warmup_worker() -> None:
    """Process pool initializer: load TensorFlow/basic_pitch once per process."""
    import basic_pitch.inference  # noqa: F401


def _transcribe_to_midi(audio_path: str, midi_path: str) -> None:
    """Runs in a child process. Imported lazily so the main process stays light."""
    from basic_pitch.inference import predict

    _, midi_data, _ = predict(audio_path)
    midi_data.write(midi_path)


class BasicPitchTranscriber(Transcriber):
    """Runs basic_pitch in a shared process pool (CPU-bound work)."""

    def __init__(self, max_workers: int) -> None:
        self._max_workers = max_workers
        self._pool = self._create_pool()

    def _create_pool(self) -> ProcessPoolExecutor:
        # "spawn" is safer than "fork" for TensorFlow and a multithreaded parent
        return ProcessPoolExecutor(
            max_workers=self._max_workers,
            mp_context=multiprocessing.get_context("spawn"),
            initializer=_warmup_worker,
        )

    async def transcribe(self, audio_path: Path, midi_path: Path) -> None:
        pool = self._pool
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                pool, _transcribe_to_midi, str(audio_path), str(midi_path)
            )
        except BrokenProcessPool:
            # A child died (e.g. OOM) -> the pool is unusable, create a new one.
            if self._pool is pool:
                logger.error("Process pool is broken, recreating")
                self._pool = self._create_pool()
                pool.shutdown(wait=False)
            raise

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
