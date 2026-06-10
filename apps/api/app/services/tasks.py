from datetime import UTC, datetime, timedelta

from sqlalchemy import asc, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.models import DownloadTask, TaskEvent, User
from app.services.storage import ObjectStorage
from video_downloader_shared.states import ACTIVE_TASK_STATES, TaskState


def assert_concurrency_allowed(db: Session, user: User) -> None:
    settings = get_settings()
    reconcile_stale_active_tasks(db)
    active_values = [state.value for state in ACTIVE_TASK_STATES]
    day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    if user.daily_task_quota >= 0:
        daily_count = db.scalar(
            select(func.count())
            .select_from(DownloadTask)
            .where(DownloadTask.user_id == user.id, DownloadTask.created_at >= day_start)
        )
        if daily_count is not None and daily_count >= user.daily_task_quota:
            raise AppError(ErrorCode.LIMIT_EXCEEDED, "今日下载任务额度已用完，请明天再试", 429)

    storage_used = db.scalar(
        select(func.coalesce(func.sum(DownloadTask.object_size), 0))
        .select_from(DownloadTask)
        .where(DownloadTask.user_id == user.id, DownloadTask.object_key.is_not(None))
    )
    if user.storage_quota_bytes >= 0 and storage_used is not None and storage_used >= user.storage_quota_bytes:
        raise AppError(ErrorCode.LIMIT_EXCEEDED, "当前账号存储额度已用完，请等待过期清理或联系管理员", 429)

    global_count = db.scalar(
        select(func.count()).select_from(DownloadTask).where(DownloadTask.state.in_(active_values))
    )
    if global_count and global_count >= settings.global_download_concurrency:
        raise AppError(ErrorCode.LIMIT_EXCEEDED, "当前全局下载任务已满，请稍后再试", 429)

    user_count = db.scalar(
        select(func.count())
        .select_from(DownloadTask)
        .where(DownloadTask.user_id == user.id, DownloadTask.state.in_(active_values))
    )
    user_limit = user.concurrent_task_quota if user.concurrent_task_quota >= 0 else settings.per_user_download_concurrency
    if user_count and user_count >= user_limit:
        raise AppError(ErrorCode.LIMIT_EXCEEDED, "当前账号已有下载任务在执行，请稍后再试", 429)


def add_task_event(db: Session, task: DownloadTask, state: TaskState | str, message: str | None = None) -> None:
    value = state.value if isinstance(state, TaskState) else state
    db.add(TaskEvent(task_id=task.id, state=value, message=message))


def list_task_events(db: Session, task: DownloadTask) -> list[TaskEvent]:
    return list(
        db.scalars(
            select(TaskEvent).where(TaskEvent.task_id == task.id).order_by(asc(TaskEvent.created_at), asc(TaskEvent.id))
        )
    )


def annotate_latest_attempts(db: Session, tasks: list[DownloadTask]) -> list[DownloadTask]:
    task_ids = [task.id for task in tasks]
    if not task_ids:
        return tasks
    superseded_ids = set(
        db.scalars(
            select(DownloadTask.retry_of_task_id).where(
                DownloadTask.retry_of_task_id.in_(task_ids),
                DownloadTask.retry_of_task_id.is_not(None),
            )
        )
    )
    for task in tasks:
        task._is_latest_attempt = task.id not in superseded_ids
    return tasks


def get_owned_task(db: Session, user: User, task_id: str) -> DownloadTask:
    task = db.get(DownloadTask, task_id)
    if not task or task.user_id != user.id:
        raise AppError(ErrorCode.NOT_FOUND, "任务不存在", 404)
    annotate_latest_attempts(db, [task])
    return task


def cancel_task(db: Session, task: DownloadTask) -> DownloadTask:
    if task.state not in {TaskState.QUEUED.value, TaskState.RUNNING.value}:
        raise AppError(ErrorCode.INVALID_STATE, "当前任务状态不支持取消", 409)
    task.state = TaskState.CANCELED.value
    task.failure_code = None
    task.failure_reason = "用户已取消任务"
    task.updated_at = datetime.now(UTC)
    add_task_event(db, task, TaskState.CANCELED, "用户已取消任务")
    db.commit()
    db.refresh(task)
    return task


def retry_task(db: Session, user: User, task: DownloadTask) -> DownloadTask:
    if _has_retry_child(db, task):
        raise AppError(ErrorCode.RETRY_SUPERSEDED, "该任务已有新的重试任务，请在最新任务上操作", 409)
    if not _is_retryable_task(task):
        raise AppError(ErrorCode.INVALID_STATE, "当前任务状态不支持重试", 409)
    assert_concurrency_allowed(db, user)
    attempt_no = (task.attempt_no or 1) + 1
    new_task = DownloadTask(
        user_id=user.id,
        source_url=task.source_url,
        title=task.title,
        cover_url=task.cover_url,
        duration_seconds=task.duration_seconds,
        format_id=task.format_id or "best",
        format_label=task.format_label,
        retry_of_task_id=task.id,
        attempt_no=attempt_no,
        state=TaskState.QUEUED.value,
        progress=0,
    )
    db.add(new_task)
    db.flush()
    add_task_event(db, new_task, TaskState.QUEUED, f"第 {attempt_no} 次尝试已创建，等待下载")
    add_task_event(db, task, task.state, f"已创建重试任务：{new_task.id}")
    db.commit()
    db.refresh(new_task)
    return new_task


def cleanup_expired_task_outputs(db: Session) -> int:
    now = datetime.now(UTC)
    tasks = db.scalars(
        select(DownloadTask).where(
            DownloadTask.state == TaskState.SUCCEEDED.value,
            DownloadTask.object_key.is_not(None),
            DownloadTask.expires_at.is_not(None),
            DownloadTask.expires_at <= now,
        )
    )
    storage = ObjectStorage()
    removed = 0
    for task in tasks:
        try:
            storage.delete_object(task.object_key)
        except Exception:
            pass
        task.object_key = None
        task.failure_code = "retention_expired"
        task.failure_reason = "文件保留时间已过期并已清理，历史记录仍保留"
        task.updated_at = datetime.now(UTC)
        add_task_event(db, task, task.state, "过期文件已清理，历史记录已保留")
        removed += 1
    if removed:
        db.commit()
    return removed


def reconcile_stale_active_tasks(db: Session) -> int:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.max_task_runtime_seconds)
    active_values = [state.value for state in ACTIVE_TASK_STATES]
    tasks = db.scalars(select(DownloadTask).where(DownloadTask.state.in_(active_values))).all()
    reconciled = 0
    for task in tasks:
        reference_time = _as_utc(task.updated_at or task.created_at)
        if reference_time and reference_time <= cutoff:
            task.state = TaskState.FAILED.value
            task.progress = min(task.progress or 0, 99)
            task.failure_code = "task_timeout"
            task.failure_reason = "任务运行超过最大时长限制，已自动标记失败"
            task.updated_at = datetime.now(UTC)
            add_task_event(db, task, TaskState.FAILED, task.failure_reason)
            reconciled += 1
    if reconciled:
        db.commit()
    return reconciled


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _has_retry_child(db: Session, task: DownloadTask) -> bool:
    return bool(
        db.scalar(
            select(func.count())
            .select_from(DownloadTask)
            .where(DownloadTask.retry_of_task_id == task.id)
        )
    )


def _is_retryable_task(task: DownloadTask) -> bool:
    if task.state in {TaskState.FAILED.value, TaskState.CANCELED.value}:
        return True
    if task.state != TaskState.SUCCEEDED.value:
        return False
    if not task.object_key or task.failure_code == "retention_expired":
        return True
    expires_at = _as_utc(task.expires_at)
    return bool(expires_at and expires_at <= datetime.now(UTC))
