from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from src.downloads.schemas import ArtifactSummary, DownloadJob, JobError
from src.media.schemas import InspectedMedia, MediaFormat


def test_media_schemas_map_objects_and_serialize_utc() -> None:
    format_id = uuid.uuid4()
    media = InspectedMedia.from_model(
        SimpleNamespace(
            id=uuid.uuid4(),
            title="title",
            extractor_key="example",
            inspect_expires_at=datetime(2030, 1, 1),
            formats=[
                SimpleNamespace(
                    id=format_id,
                    label="360p",
                    width=640,
                    height=360,
                    fps=Decimal("29.97"),
                    container="mp4",
                    video_codec="avc1",
                    audio_codec="mp4a",
                    estimated_size_bytes=100,
                    requires_merge=False,
                )
            ],
        )
    )
    assert media.platform == "example"
    assert media.formats[0].fps == 29.97
    assert media.model_dump(mode="json")["expires_at"].endswith("Z")
    with pytest.raises(ValidationError):
        MediaFormat(
            id=format_id,
            label="360p",
            container="mp4",
            video_codec="avc1",
            audio_codec="mp4a",
            requires_merge=False,
            extra="no",
        )


def test_download_schemas_map_artifact_and_error() -> None:
    now = datetime(2030, 1, 1)
    artifact = ArtifactSummary.from_model(
        SimpleNamespace(
            file_name="video.mp4",
            content_type="video/mp4",
            size_bytes=10,
            sha256="a" * 64,
            expires_at=now,
        )
    )
    job = DownloadJob.from_model(
        SimpleNamespace(
            id=uuid.uuid4(),
            status="succeeded",
            stage=None,
            progress_percent=100,
            downloaded_bytes=10,
            total_bytes=10,
            error_code="bad",
            error_message="failure",
            artifact=artifact,
            created_at=now,
            updated_at=now,
        )
    )
    assert job.error == JobError(code="bad", message="failure")
    assert job.artifact is artifact
    assert job.model_dump(mode="json")["created_at"].endswith("Z")
    with pytest.raises(ValidationError):
        ArtifactSummary(
            file_name="x", content_type="x", size_bytes=0, sha256="bad", expires_at=now
        )
