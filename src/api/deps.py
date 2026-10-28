from typing import Annotated

from fastapi import Depends, Request

from src.services.task_service import TaskService


def get_service(request: Request) -> TaskService:
    return request.app.state.service


ServiceDep = Annotated[TaskService, Depends(get_service)]
