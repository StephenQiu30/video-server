from datetime import UTC, datetime
import hashlib
import hmac
import secrets
import time
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.deps import get_current_user
from app.models import DownloadTask, User
from app.schemas import DownloadLinkResponse, TaskCreate, TaskEventRead, TaskRead
from app.services.queue import enqueue_download_task
from app.services.storage import ObjectStorage
from app.services.tasks import (
    add_task_event,
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
    query = (
        select(DownloadTask)
        .where(DownloadTask.user_id == current_user.id)
        .order_by(desc(DownloadTask.created_at))
    )
    if state:
        valid_states = {item.value for item in TaskState}
        if state not in valid_states:
            raise AppError("invalid_state", "任务状态筛选值无效", 422)
        query = query.where(DownloadTask.state == state)
    if limit:
        query = query.limit(limit)
    return list(db.scalars(query))


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
    ttl = get_settings().presigned_url_ttl_seconds
    expires = int(time.time()) + ttl
    signature = _sign_download_url(task.id, expires)
    base_url = request.url_for("download_task_file", task_id=task.id)
    return DownloadLinkResponse(url=f"{base_url}?expires={expires}&signature={signature}", expires_in_seconds=ttl)


@router.get("/{task_id}/download", name="download_task_file")
def download_task_file(
    task_id: str,
    expires: int,
    signature: str,
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    _verify_download_signature(task_id, expires, signature)
    cleanup_expired_task_outputs(db)
    task = db.get(DownloadTask, task_id)
    if not task:
        raise AppError("not_found", "任务不存在", 404)
    _assert_downloadable(task)
    response = ObjectStorage().get_object(task.object_key)
    body = response["Body"]
    filename = task.output_filename or task.object_key.rsplit("/", 1)[-1]
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    if response.get("ContentLength") is not None:
        headers["Content-Length"] = str(response["ContentLength"])
    return StreamingResponse(
        _iter_object_body(body),
        media_type=response.get("ContentType") or "application/octet-stream",
        headers=headers,
    )


def _assert_downloadable(task: DownloadTask) -> None:
    if task.state != TaskState.SUCCEEDED.value:
        raise AppError("invalid_state", "任务尚未完成，暂不能获取下载链接", 409)
    if not task.object_key:
        raise AppError("retention_expired", "文件不存在或已过期，请重新创建任务", 410)
    if task.expires_at and _as_utc(task.expires_at) <= datetime.now(UTC):
        raise AppError("retention_expired", "文件保留时间已过期，请重新创建任务", 410)


def _sign_download_url(task_id: str, expires: int) -> str:
    settings = get_settings()
    payload = f"{task_id}:{expires}".encode("utf-8")
    secret = settings.jwt_secret_key.encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def _verify_download_signature(task_id: str, expires: int, signature: str) -> None:
    if expires <= int(time.time()):
        raise AppError("download_link_expired", "下载链接已过期，请重新获取", 403)
    expected = _sign_download_url(task_id, expires)
    if not secrets.compare_digest(expected, signature):
        raise AppError("invalid_signature", "下载链接签名无效，请重新获取", 403)


def _iter_object_body(body):
    try:
        yield from body.iter_chunks(chunk_size=1024 * 1024)
    finally:
        body.close()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
