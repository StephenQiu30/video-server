from datetime import UTC, datetime
import asyncio
import json
import time
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import SessionLocal, get_db
from app.deps import get_current_user
from app.models import DownloadTask, User
from app.schemas import DownloadLinkResponse, TaskCreate, TaskEventRead, TaskRead
from app.services.queue import enqueue_download_task
from app.services.storage import ObjectStorage
from app.services.pdf import PDFService
from app.services.tasks import (
    add_task_event,
    annotate_latest_attempts,
    assert_concurrency_allowed,
    cancel_task,
    cleanup_expired_task_outputs,
    get_owned_task,
    list_task_events,
    reconcile_stale_active_tasks,
    retry_task,
)
from app.utils.url import normalize_user_url
from video_downloader_shared.states import TaskState

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=201)
def create_task(
    payload: TaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DownloadTask:
    source_url = normalize_user_url(payload.url)
    assert_concurrency_allowed(db, current_user)
    task = DownloadTask(
        user_id=current_user.id,
        source_url=source_url,
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
    state: Annotated[str | None, Query()] = None,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
) -> list[DownloadTask]:
    reconcile_stale_active_tasks(db)
    cleanup_expired_task_outputs(db)
    return _list_user_tasks(db, current_user.id, state, limit)


@router.get("/stream")
async def stream_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> StreamingResponse:
    user_id = current_user.id

    async def event_generator():
        last_payload: str | None = None
        while True:
            with SessionLocal() as stream_db:
                tasks = _list_user_tasks(stream_db, user_id, None, limit)
                payload = json.dumps(
                    {
                        "type": "tasks",
                        "tasks": [
                            TaskRead.model_validate(task).model_dump(mode="json")
                            for task in tasks
                        ],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload != last_payload:
                yield f"event: tasks\ndata: {payload}\n\n"
                last_payload = payload
            else:
                yield ": keep-alive\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DownloadTask:
    reconcile_stale_active_tasks(db)
    return get_owned_task(db, current_user, task_id)


@router.post("/{task_id}/cancel", response_model=TaskRead)
def cancel_download_task(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DownloadTask:
    return cancel_task(db, get_owned_task(db, current_user, task_id))


@router.get("/{task_id}/events", response_model=list[TaskEventRead])
def get_task_events(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list:
    return list_task_events(db, get_owned_task(db, current_user, task_id))


@router.post("/{task_id}/retry", response_model=TaskRead, status_code=201)
def retry_download_task(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DownloadTask:
    new_task = retry_task(db, current_user, get_owned_task(db, current_user, task_id))
    try:
        enqueue_download_task(new_task.id)
    except AppError:
        new_task.state = TaskState.FAILED.value
        new_task.failure_code = "queue_unavailable"
        new_task.failure_reason = "任务队列暂不可用，请稍后重试"
        add_task_event(db, new_task, TaskState.FAILED, new_task.failure_reason)
        db.commit()
        raise
    return new_task


@router.get("/{task_id}/download-link", response_model=DownloadLinkResponse)
def get_download_link(
    task_id: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DownloadLinkResponse:
    cleanup_expired_task_outputs(db)
    task = get_owned_task(db, current_user, task_id)
    _assert_downloadable(task)
    settings = get_settings()
    url = ObjectStorage().presign_download_url(task.object_key)
    return DownloadLinkResponse(url=url, expires_in_seconds=settings.presigned_url_ttl_seconds)


@router.get("/{task_id}/pdf")
def export_task_pdf(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    task = get_owned_task(db, current_user, task_id)
    if task.state != TaskState.SUCCEEDED.value:
        raise AppError("invalid_state", "任务尚未完成，无法导出报告", 409)
    
    pdf_content = PDFService().generate_task_report(task)
    filename = f"report_{task.id[:8]}.pdf"
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers=headers,
    )


def _assert_downloadable(task: DownloadTask) -> None:
    if task.state != TaskState.SUCCEEDED.value:
        raise AppError("invalid_state", "任务尚未完成，暂不能获取下载链接", 409)
    if not task.object_key:
        raise AppError("retention_expired", "文件不存在或已过期，请重新创建任务", 410)
    if task.expires_at:
        expires_at = task.expires_at if task.expires_at.tzinfo else task.expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            raise AppError("retention_expired", "文件保留时间已过期，请重新创建任务", 410)


def _list_user_tasks(db: Session, user_id: int, state: str | None = None, limit: int | None = None) -> list[DownloadTask]:
    query = (
        select(DownloadTask)
        .where(DownloadTask.user_id == user_id)
        .order_by(desc(DownloadTask.created_at))
    )
    if state:
        valid_states = {item.value for item in TaskState}
        if state not in valid_states:
            raise AppError("invalid_state", "任务状态筛选值无效", 422)
        query = query.where(DownloadTask.state == state)
    if limit:
        query = query.limit(limit)
    return annotate_latest_attempts(db, list(db.scalars(query)))
