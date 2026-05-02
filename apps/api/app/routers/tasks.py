from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.deps import get_current_user
from app.models import DownloadTask, User
from app.schemas import DownloadLinkResponse, TaskCreate, TaskRead
from app.services.queue import enqueue_download_task
from app.services.storage import ObjectStorage
from app.services.tasks import add_task_event, assert_concurrency_allowed, cancel_task, get_owned_task
from video_downloader_shared.states import TaskState

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=201)
def create_task(
    payload: TaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DownloadTask:
    assert_concurrency_allowed(db, current_user)
    task = DownloadTask(
        user_id=current_user.id,
        source_url=str(payload.url),
        title=payload.title,
        cover_url=payload.cover_url,
        duration_seconds=payload.duration_seconds,
        format_id=payload.format_id or "best",
        format_label=payload.format_label,
        state=TaskState.QUEUED.value,
        progress=0,
    )
    db.add(task)
    db.flush()
    add_task_event(db, task, TaskState.QUEUED, "任务已创建，等待下载")
    db.commit()
    db.refresh(task)
    try:
        enqueue_download_task(task.id)
    except AppError:
        task.state = TaskState.FAILED.value
        task.failure_code = "queue_unavailable"
        task.failure_reason = "任务队列暂不可用，请稍后重试"
        add_task_event(db, task, TaskState.FAILED, task.failure_reason)
        db.commit()
        raise
    return task


@router.get("", response_model=list[TaskRead])
def list_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[DownloadTask]:
    return list(
        db.scalars(
            select(DownloadTask)
            .where(DownloadTask.user_id == current_user.id)
            .order_by(desc(DownloadTask.created_at))
        )
    )


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DownloadTask:
    return get_owned_task(db, current_user, task_id)


@router.post("/{task_id}/cancel", response_model=TaskRead)
def cancel_download_task(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DownloadTask:
    return cancel_task(db, get_owned_task(db, current_user, task_id))


@router.get("/{task_id}/download-link", response_model=DownloadLinkResponse)
def get_download_link(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DownloadLinkResponse:
    task = get_owned_task(db, current_user, task_id)
    if task.state != TaskState.SUCCEEDED.value or not task.object_key:
        raise AppError("invalid_state", "任务尚未完成，暂不能获取下载链接", 409)
    if task.expires_at and task.expires_at <= datetime.now(UTC):
        raise AppError("retention_expired", "文件保留时间已过期，请重新创建任务", 410)
    url = ObjectStorage().presign_download_url(task.object_key)
    return DownloadLinkResponse(url=url, expires_in_seconds=get_settings().presigned_url_ttl_seconds)
