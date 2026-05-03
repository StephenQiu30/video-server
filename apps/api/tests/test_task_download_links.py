from datetime import UTC, datetime, timedelta
import time

from app.core.errors import AppError
from app.models import DownloadTask
from app.routers.tasks import _assert_downloadable, _sign_download_url, _verify_download_signature
from video_downloader_shared.states import TaskState


def test_download_signature_roundtrip() -> None:
    expires = int(time.time()) + 60
    signature = _sign_download_url("task-1", expires)

    _verify_download_signature("task-1", expires, signature)


def test_download_signature_rejects_forgery() -> None:
    expires = int(time.time()) + 60
    try:
        _verify_download_signature("task-1", expires, "bad")
    except AppError as exc:
        assert exc.status_code == 403
        assert exc.code == "invalid_signature"
    else:
        raise AssertionError("expected invalid signature")


def test_assert_downloadable_rejects_expired_retention() -> None:
    task = DownloadTask(
        state=TaskState.SUCCEEDED.value,
        object_key="users/1/tasks/task-1/video.mp4",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    try:
        _assert_downloadable(task)
    except AppError as exc:
        assert exc.status_code == 410
        assert exc.code == "retention_expired"
    else:
        raise AssertionError("expected expired retention")
