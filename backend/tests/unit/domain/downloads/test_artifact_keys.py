from __future__ import annotations

from uuid import uuid4

import pytest
from app.application.download_execution.artifact import artifact_object_key
from app.application.download_execution.errors import ArtifactValidationError
from app.domain.downloads import build_artifact_object_key
from app.infrastructure.database.completion_repository import (
    build_artifact_object_key as persistence_artifact_object_key,
)


@pytest.mark.parametrize(
    ("container", "filename"),
    [("mp4", "video.mp4"), ("webm", "video.webm"), ("zip", "images.zip")],
)
def test_artifact_key_is_consistent_between_upload_and_persistence(
    container: str, filename: str
) -> None:
    job_id = uuid4()
    expected = f"downloads/{job_id}/1/{filename}"

    assert build_artifact_object_key(job_id, 1, container) == expected
    assert artifact_object_key(job_id, 1, container) == expected
    assert persistence_artifact_object_key(job_id, 1, container) == expected


@pytest.mark.parametrize(
    ("attempt", "container"), [(0, "mp4"), (1, "mkv"), (1, "")]
)
def test_artifact_key_rejects_invalid_identity(attempt: int, container: str) -> None:
    job_id = uuid4()

    with pytest.raises(ValueError):
        build_artifact_object_key(job_id, attempt, container)

    with pytest.raises(ArtifactValidationError):
        artifact_object_key(job_id, attempt, container)
