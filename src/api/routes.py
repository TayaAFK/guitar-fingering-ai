from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.api.deps import ServiceDep
from src.api.schemas import StatusResponse, UploadResponse, result_url, status_url
from src.domain.errors import QueueFullError, EmptyUploadError, UploadTooLargeError, DurationExceedError
from src.domain.models import TaskError, TaskStatus, ErrorCode, CLIENT_ERROR_CODES

ALLOWED_CONTENT_TYPES = {"video/mp4", "video/quicktime"}


router = APIRouter()


@router.post("/upload", status_code=202, response_model=UploadResponse)
async def upload_video(file: UploadFile, service: ServiceDep) -> UploadResponse:
    if not file.content_type:
        raise HTTPException(400, "Unable to check content type")
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            415,
            f"Unsupported content type. Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    try:
        task = await service.submit(file)
    except QueueFullError:
        raise HTTPException(
            503,
            "The server is busy, please try again later",
            headers={"Retry-After": "30"},
        ) from None
    except EmptyUploadError:
        raise HTTPException(
            400, "Upload file is empty"
        )
    except UploadTooLargeError as exc:
        raise HTTPException(
            413, exc.msg
        )
    except DurationExceedError as exc:
        raise HTTPException(
            400, exc.msg
        )

    return UploadResponse(
        task_id=task.id,
        status=task.status,
        status_url=status_url(task.id),
        result_url=result_url(task.id),
        created_at=task.created_at,
    )


@router.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str, service: ServiceDep) -> StatusResponse:
    task = await service.get(task_id)
    if task is None:
        raise _not_found()
    return StatusResponse.from_task(task)


@router.get(
    "/result/{task_id}",
    response_class=FileResponse,
    responses={
        404: {"description": "Task not found or expired"},
        409: {"description": "Task is not finished yet"},
        422: {"description": "Task failed because of the input file"},
        500: {"description": "Task failed because of a server error"},
    },
)
async def get_result(task_id: str, service: ServiceDep):
    task = await service.get(task_id)
    if task is None:
        raise _not_found()

    if task.status is TaskStatus.FAILED:
        error = task.error or TaskError(
            code=ErrorCode.INTERNAL_ERROR, message="Processing failed"
        )
        status_code = 422 if error.code in CLIENT_ERROR_CODES else 500
        raise HTTPException(
            status_code, {"code": error.code.value, "message": error.message}
        )

    if task.status is not TaskStatus.COMPLETED:
        raise HTTPException(
            409,
            {
                "code": "not_ready",
                "message": "The result is not ready yet",
                "status": task.status.value,
            },
            headers={"Retry-After": "5"},
        )

    path = service.result_path(task_id)
    if not path.exists():
        raise _not_found()

    stem = Path(task.filename).stem if task.filename else task.id
    return FileResponse(path, media_type="audio/midi", filename=f"{stem}.mid")


def _not_found() -> HTTPException:
    return HTTPException(
        404, {"code": "task_not_found", "message": "Task not found or already expired"}
    )
