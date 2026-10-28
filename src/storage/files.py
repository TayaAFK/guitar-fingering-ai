import shutil
from pathlib import Path


class TaskFiles:
    """Per-task working directory on the local filesystem.

    Layout: <root>/<task_id>/{input.bin, audio.wav, result.mid}
    Replace with an S3 / shared-volume implementation once workers
    move to separate machines.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def _dir(self, task_id: str) -> Path:
        return self._root / task_id

    def input_path(self, task_id: str) -> Path:
        return self._dir(task_id) / "input.bin"

    def audio_path(self, task_id: str) -> Path:
        return self._dir(task_id) / "audio.wav"

    def result_path(self, task_id: str) -> Path:
        return self._dir(task_id) / "result.mid"

    def create(self, task_id: str) -> None:
        self._dir(task_id).mkdir(parents=True)

    def remove_intermediate(self, task_id: str) -> None:
        self.input_path(task_id).unlink(missing_ok=True)
        self.audio_path(task_id).unlink(missing_ok=True)

    def remove(self, task_id: str) -> None:
        shutil.rmtree(self._dir(task_id), ignore_errors=True)
