"""Translate persistence records into application-owned contracts."""

from app.application.downloads import (
    ArtifactSnapshot,
    FormatSnapshot,
    InspectionSaveResult,
    InspectionSnapshot,
    JobSaveResult,
    JobSnapshot,
)
from app.infrastructure.database import (
    ArtifactSnapshot as StoredArtifact,
)
from app.infrastructure.database import (
    InspectionCreateResult as StoredInspectionResult,
)
from app.infrastructure.database import (
    InspectionSnapshot as StoredInspection,
)
from app.infrastructure.database import JobCreateResult as StoredJobResult
from app.infrastructure.database import JobSnapshot as StoredJob


def inspection_result(value: StoredInspectionResult) -> InspectionSaveResult:
    return InspectionSaveResult(
        inspection=inspection_snapshot(value.inspection),
        created=value.created,
    )


def inspection_snapshot(value: StoredInspection) -> InspectionSnapshot:
    return InspectionSnapshot(
        id=value.id,
        owner_hash=value.owner_hash,
        request_fingerprint=value.request_fingerprint,
        extractor_key=value.extractor_key,
        provider_media_id=value.provider_media_id,
        title=value.title,
        duration_seconds=value.duration_seconds,
        metadata=dict(value.metadata),
        expires_at=value.expires_at,
        formats=tuple(
            FormatSnapshot(
                id=item.id,
                display_name=item.display_name,
                plan_fingerprint=item.plan_fingerprint,
                semantic_plan=dict(item.semantic_plan),
                provider_hints=dict(item.provider_hints),
                expires_at=item.expires_at,
            )
            for item in value.formats
        ),
    )


def job_result(value: StoredJobResult) -> JobSaveResult:
    return JobSaveResult(job=job_snapshot(value.job), created=value.created)


def job_snapshot(value: StoredJob) -> JobSnapshot:
    return JobSnapshot(
        id=value.id,
        inspection_id=value.inspection_id,
        format_id=value.format_id,
        owner_hash=value.owner_hash,
        request_fingerprint=value.request_fingerprint,
        semantic_plan=dict(value.semantic_plan),
        status=value.status,
        stage=value.stage,
        progress=value.progress,
        attempt=value.attempt,
        max_attempts=value.max_attempts,
        version=value.version,
        lease_owner=value.lease_owner,
        lease_expires_at=value.lease_expires_at,
        heartbeat_at=value.heartbeat_at,
        started_at=value.started_at,
        retry_at=value.retry_at,
        finished_at=value.finished_at,
        error_code=value.error_code,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def artifact_snapshot(value: StoredArtifact) -> ArtifactSnapshot:
    return ArtifactSnapshot(
        id=value.id,
        job_id=value.job_id,
        attempt=value.attempt,
        bucket=value.bucket,
        object_key=value.object_key,
        sha256=value.sha256,
        size_bytes=value.size_bytes,
        duration_ms=value.duration_ms,
        container=value.container,
        content_type=value.content_type,
        media_metadata=dict(value.media_metadata),
        expires_at=value.expires_at,
    )
