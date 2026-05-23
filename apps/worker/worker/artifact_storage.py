from datetime import UTC, datetime, timedelta

from app.models import DownloadTask
from app.services.storage import ObjectStorage
from worker.domain import DownloadArtifact, StoredArtifact
from worker.failures import JobFailure


def upload_artifact(task: DownloadTask, artifact: DownloadArtifact) -> StoredArtifact:
    object_key = f"users/{task.user_id}/tasks/{task.id}/{artifact.filename}"
    try:
        ObjectStorage().upload_file(str(artifact.path), object_key)
    except Exception as exc:
        raise JobFailure("storage_failed", "文件上传对象存储失败") from exc
    return StoredArtifact(
        object_key=object_key,
        object_size=artifact.size_bytes,
        expires_at=datetime.now(UTC) + timedelta(hours=task.user.file_retention_hours),
    )


def delete_artifact(object_key: str) -> None:
    ObjectStorage().delete_object(object_key)
