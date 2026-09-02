from __future__ import annotations

import asyncio
import hashlib
import hmac
import math
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.domain.downloads import MediaKind, build_artifact_object_key

from .errors import ArtifactValidationError
from .ports import RunnerArtifactView

_SHA256 = re.compile(r"[0-9a-f]{64}")
_CONTAINER_TYPES = {
    "mp4": "video/mp4",
    "webm": "video/webm",
    "zip": "application/zip",
}


@dataclass(frozen=True, slots=True)
class VerifiedArtifact:
    path: Path
    size_bytes: int
    sha256: str
    duration_ms: int
    container: str
    content_type: str
    video_streams: int
    audio_streams: int
    media_kind: MediaKind = MediaKind.VIDEO
    asset_count: int = 0


async def verify_artifact(
    artifact: RunnerArtifactView,
    *,
    task_id: str,
    shared_root: Path,
    max_size_bytes: int,
) -> VerifiedArtifact:
    return await asyncio.to_thread(
        _verify_artifact,
        artifact,
        task_id,
        shared_root,
        max_size_bytes,
    )


def artifact_object_key(job_id: UUID, attempt: int, container: str) -> str:
    try:
        return build_artifact_object_key(job_id, attempt, container)
    except ValueError as exc:
        raise ArtifactValidationError("invalid artifact identity") from exc


def _verify_artifact(
    artifact: RunnerArtifactView,
    task_id: str,
    shared_root: Path,
    max_size_bytes: int,
) -> VerifiedArtifact:
    if artifact.task_id != task_id:
        raise ArtifactValidationError("runner task identity mismatch")
    try:
        workspace_stat = artifact.workspace.lstat()
        artifact_stat = artifact.artifact.lstat()
        root = shared_root.resolve(strict=True)
        workspace = artifact.workspace.resolve(strict=True)
        path = artifact.artifact.resolve(strict=True)
    except OSError as exc:
        raise ArtifactValidationError("artifact is unavailable") from exc
    if (
        not stat.S_ISDIR(workspace_stat.st_mode)
        or stat.S_ISLNK(workspace_stat.st_mode)
        or not stat.S_ISREG(artifact_stat.st_mode)
        or stat.S_ISLNK(artifact_stat.st_mode)
        or not workspace.is_relative_to(root)
        or not path.is_relative_to(workspace)
    ):
        raise ArtifactValidationError("artifact path is unsafe")
    actual_size = artifact_stat.st_size
    if (
        actual_size <= 0
        or actual_size > max_size_bytes
        or actual_size != artifact.size_bytes
    ):
        raise ArtifactValidationError("artifact size is invalid")
    if _SHA256.fullmatch(artifact.sha256) is None:
        raise ArtifactValidationError("artifact digest is invalid")
    digest = _file_sha256(path)
    if not hmac.compare_digest(digest, artifact.sha256):
        raise ArtifactValidationError("artifact digest does not match")
    if artifact.media_kind in {
        MediaKind.IMAGE_GALLERY,
        MediaKind.VIDEO_COLLECTION,
    }:
        if (
            artifact.container != "zip"
            or artifact.video_streams != 0
            or artifact.audio_streams != 0
            or artifact.asset_count < 1
        ):
            raise ArtifactValidationError("archive artifact metadata is invalid")
    elif (
        not math.isfinite(artifact.duration_seconds)
        or artifact.duration_seconds <= 0
        or artifact.video_streams < 1
        or artifact.audio_streams < 1
        or artifact.container not in {"mp4", "webm"}
    ):
        raise ArtifactValidationError("artifact media metadata is invalid")
    content_type = _CONTAINER_TYPES.get(artifact.container)
    if content_type is None:
        raise ArtifactValidationError("artifact container is unsupported")
    return VerifiedArtifact(
        path=path,
        size_bytes=actual_size,
        sha256=digest,
        duration_ms=max(1, round(artifact.duration_seconds * 1000)),
        container=artifact.container,
        content_type=content_type,
        video_streams=artifact.video_streams,
        audio_streams=artifact.audio_streams,
        media_kind=artifact.media_kind,
        asset_count=artifact.asset_count,
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
