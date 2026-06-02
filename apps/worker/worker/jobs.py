from pathlib import Path
import shutil

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import DownloadTask
from app.services.tasks import add_task_event, cleanup_expired_task_outputs
from video_downloader_shared.states import TaskState
from worker.ai_pipeline import process_ai_pipeline
from worker.artifact_storage import delete_artifact, upload_artifact
from worker.download_runner import (
    apply_browser_cookie_options,
    apply_download_resilience_options,
    build_cookie_args,
    download_task_artifact,
    resolve_output_path,
)
from worker.failures import (
    JobFailure,
    failure_code,
    failure_info_from_exception,
    format_failure_reason,
    raise_task_canceled,
)
from worker.media_probe import assert_artifact_size, assert_media_tools_available, artifact_from_path, probe_with_ffprobe
from worker.domain import WorkerStage


def process_download_task(task_id: str) -> None:
    db = SessionLocal()
    task_work_dir: Path | None = None
    try:
        task = db.get(DownloadTask, task_id)
        if not task or _should_skip_task(task):
            return

        task_work_dir = _task_work_dir(task)
        _mark_running(db, task)
        assert_media_tools_available()

        artifact = download_task_artifact(task, db, task_work_dir, _is_canceled)
        if _is_canceled(db, task):
            return

        assert_artifact_size(artifact, task)
        add_task_event(db, task, TaskState.RUNNING, "开始校验媒体文件")
        db.commit()
        probe_with_ffprobe(artifact, db, task)
        if _is_canceled(db, task):
            return

        add_task_event(db, task, TaskState.RUNNING, "开始上传到私有对象存储")
        db.commit()
        stored = upload_artifact(task, artifact)
        if _is_canceled(db, task):
            delete_artifact(stored.object_key)
            return

        task.state = TaskState.SUCCEEDED.value
        task.progress = 100
        task.output_filename = artifact.filename
        task.object_key = stored.object_key
        task.object_size = stored.object_size
        task.expires_at = stored.expires_at
        add_task_event(db, task, TaskState.SUCCEEDED, "文件已保存到私有对象存储")
        db.commit()

        process_ai_pipeline(db, task, artifact)
    except Exception as exc:
        _mark_failed(db, task_id, exc)
        raise
    finally:
        _cleanup_task_work_dir(task_work_dir)
        db.close()


def _should_skip_task(task: DownloadTask) -> bool:
    if task.state == TaskState.CANCELED.value:
        return True
    if task.state == TaskState.SUCCEEDED.value and task.object_key:
        return True
    if task.state == TaskState.RUNNING.value:
        return True
    return False


def _mark_running(db: Session, task: DownloadTask) -> None:
    task.state = TaskState.RUNNING.value
    task.progress = 5
    add_task_event(db, task, TaskState.RUNNING, "Worker 已开始下载")
    db.commit()


def _is_canceled(db: Session, task: DownloadTask) -> bool:
    db.refresh(task)
    return task.state == TaskState.CANCELED.value


def _task_work_dir(task: DownloadTask) -> Path:
    settings = get_settings()
    return Path(settings.download_work_dir) / f"user-{task.user_id}" / task.id


def _cleanup_task_work_dir(task_dir: Path | None) -> None:
    if task_dir is not None:
        shutil.rmtree(task_dir, ignore_errors=True)


def _mark_failed(db: Session, task_id: str, exc: Exception) -> None:
    task = db.get(DownloadTask, task_id)
    if not task or task.state == TaskState.CANCELED.value:
        return
    info = failure_info_from_exception(exc, WorkerStage.DOWNLOAD)
    task.state = TaskState.FAILED.value
    task.failure_code = info.code.value
    task.failure_reason = info.reason
    add_task_event(db, task, TaskState.FAILED, task.failure_reason)
    db.commit()


def cleanup_expired_outputs() -> int:
    db = SessionLocal()
    try:
        return cleanup_expired_task_outputs(db)
    finally:
        db.close()


# Compatibility aliases for existing tests and external worker entrypoints.
_apply_browser_cookie_options = apply_browser_cookie_options
_build_cookie_args = build_cookie_args
_apply_download_resilience_options = apply_download_resilience_options
_failure_code = failure_code
_format_failure_reason = format_failure_reason
_raise_task_canceled = raise_task_canceled
_resolve_output_path = resolve_output_path
_assert_media_tools_available = assert_media_tools_available


def _assert_size(path: Path, task: DownloadTask) -> None:
    assert_artifact_size(artifact_from_path(path), task)


def _probe_with_ffprobe(path: Path, db: Session, task: DownloadTask) -> None:
    probe_with_ffprobe(artifact_from_path(path), db, task)


def _upload(task: DownloadTask, output_path: Path) -> str:
    return upload_artifact(task, artifact_from_path(output_path)).object_key


def _download(task: DownloadTask, db: Session, task_dir: Path) -> Path:
    return download_task_artifact(task, db, task_dir, _is_canceled).path


def _process_ai_intelligence(db: Session, task: DownloadTask, output_path: Path) -> None:
    process_ai_pipeline(db, task, artifact_from_path(output_path))
