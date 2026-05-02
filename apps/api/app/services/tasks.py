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
    if user_count and user_count >= settings.per_user_download_concurrency:
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

