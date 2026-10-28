from src.domain.models import ErrorCode


class ProcessingError(Exception):
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class TaskNotFoundError(Exception):
    pass


class QueueFullError(Exception):
    pass


class UploadTooLargeError(Exception):
    def __init__(self, limit_bytes: int):
        self.msg = f"Upload exceeds {limit_bytes} bytes"
        super().__init__(self.msg)
        self.limit_bytes = limit_bytes


class EmptyUploadError(Exception):
    pass


class DurationExceedError(Exception):
    def __init__(self, max_duration: int):
        self.msg = f"Upload duration exceeds {max_duration} seconds"
        super().__init__(self.msg)
        self.max_duration = max_duration
