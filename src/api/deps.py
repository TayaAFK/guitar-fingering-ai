from typing import Annotated

from fastapi import Depends, Request, UploadFile, HTTPException

from src.services.task_service import TaskService

ALLOWED_CONTENT_TYPES = {"video/mp4": "mp4", "video/quicktime": "mov"}


def check_upload(file: UploadFile) -> UploadFile:
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if not file.content_type or file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            415,
            f"Unsupported content type."
            f" Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )
    if ext and ext != ALLOWED_CONTENT_TYPES[file.content_type]:
        raise HTTPException(
            415,
            f"File extension does not match content type."
            f" Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES.values()))}"
        )
    return file


CheckedUploadFile = Annotated[UploadFile, Depends(check_upload)]


def get_service(request: Request) -> TaskService:
    return request.app.state.service


ServiceDep = Annotated[TaskService, Depends(get_service)]
