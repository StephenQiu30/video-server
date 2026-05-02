from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import DownloadTask, TaskEvent, User
from video_downloader_shared.states import ACTIVE_TASK_STATES, TaskState


def assert_concurrency_allowed(db: Session, user: User) -> None:
    settings = get_settings()
    active_values = [state.value for state in ACTIVE_TASK_STATES]
    day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    if user.daily_task_quota >= 0:
        daily_count = db.scalar(
            select(func.count())
            .select_from(DownloadTask)
            .where(DownloadTask.user_id == user.id, DownloadTask.created_at >= day_start)
        )
        if daily_count is not None and daily_count >= user.daily_task_quota:
            raise AppError("limit_exceeded", "今日下载任务额度已用完，请明天再试", 429)

    storage_used = db.scalar(
        select(func.coalesce(func.sum(DownloadTask.object_size), 0))
        .select_from(DownloadTask)
        .where(DownloadTask.user_id == user.id)
    )
    if user.storage_quota_bytes >= 0 and storage_used is not None and storage_used >= user.storage_quota_bytes:
        raise AppError("limit_exceeded", "当前账号存储额度已用完，请等待过期清理或联系管理员", 429)

    global_count = db.scalar(
        select(func.count()).select_from(DownloadTask).where(DownloadTask.state.in_(active_values))
    )
    if global_count and global_count >= settings.global_download_concurrency:
        raise AppError("limit_exceeded", "当前全局下载任务已满，请稍后再试", 429)

    user_count = db.scalar(
        select(func.count())
        .select_from(DownloadTask)
        .where(DownloadTask.user_id == user.id, DownloadTask.state.in_(active_values))
    )
    user_limit = user.concurrent_task_quota if user.concurrent_task_quota >= 0 else settings.per_user_download_concurrency
    if user_count and user_count >= user_limit:
        raise AppError("limit_exceeded", "当前账号已有下载任务在执行，请稍后再试", 429)


def add_task_event(db: Session, task: DownloadTask, state: TaskState | str, message: str | None = None) -> None:
    value = state.value if isinstance(state, TaskState) else state
    db.add(TaskEvent(task_id=task.id, state=value, message=message))


def get_owned_task(db: Session, user: User, task_id: str) -> DownloadTask:
    task = db.get(DownloadTask, task_id)
    if not task or task.user_id != user.id:
        raise AppError("not_found", "任务不存在", 404)
    return task


def cancel_task(db: Session, task: DownloadTask) -> DownloadTask:
    if task.state not in {TaskState.QUEUED.value, TaskState.RUNNING.value}:
        raise AppError("invalid_state", "当前任务状态不支持取消", 409)
    task.state = TaskState.CANCELED.value
    task.failure_code = None
    task.failure_reason = "用户已取消任务"
    task.updated_at = datetime.now(UTC)
    add_task_event(db, task, TaskState.CANCELED, "用户已取消任务")
    db.commit()
    db.refresh(task)
    return task
