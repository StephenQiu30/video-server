"""Convert mutable ORM rows into immutable persistence snapshots."""

from datetime import datetime

from .base import as_utc
from .contracts import (
    ArtifactSnapshot,
    DownloadHistoryItemSnapshot,
    DownloadHistoryPageSnapshot,
    DownloadHistorySummarySnapshot,
    FormatSnapshot,
    InspectionSnapshot,
    JobSnapshot,
    OutboxSnapshot,
)
from .models import (
    ArtifactRow,
    DownloadJobRow,
    MediaFormatRow,
    MediaInspectionRow,
    OutboxEventRow,
)


def inspection_snapshot(
    row: MediaInspectionRow, formats: tuple[MediaFormatRow, ...]
) -> InspectionSnapshot:
    return InspectionSnapshot(
        id=row.id,
        owner_hash=row.owner_hash,
        request_fingerprint=row.request_fingerprint,
        extractor_key=row.extractor_key,
        provider_media_id=row.provider_media_id,
        title=row.title,
        duration_seconds=row.duration_seconds,
        metadata=dict(row.metadata_json),
        expires_at=as_utc(row.expires_at),
        formats=tuple(
            FormatSnapshot(
                id=item.id,
                display_name=item.display_name,
                plan_fingerprint=item.plan_fingerprint,
                semantic_plan=dict(item.semantic_plan),
                provider_hints=dict(item.provider_hints),
                expires_at=as_utc(item.expires_at),
            )
            for item in formats
        ),
    )


def job_snapshot(row: DownloadJobRow) -> JobSnapshot:
    return JobSnapshot(
        id=row.id,
        inspection_id=row.inspection_id,
        format_id=row.format_id,
        owner_hash=row.owner_hash,
        request_fingerprint=row.request_fingerprint,
        semantic_plan=dict(row.semantic_plan),
        status=row.status,
        stage=row.stage,
        progress=row.progress,
        attempt=row.attempt,
        max_attempts=row.max_attempts,
        version=row.version,
        lease_owner=row.lease_owner,
        lease_expires_at=None
        if row.lease_expires_at is None
        else as_utc(row.lease_expires_at),
        heartbeat_at=None if row.heartbeat_at is None else as_utc(row.heartbeat_at),
        started_at=None if row.started_at is None else as_utc(row.started_at),
        retry_at=None if row.retry_at is None else as_utc(row.retry_at),
        finished_at=None if row.finished_at is None else as_utc(row.finished_at),
        error_code=row.error_code,
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
    )


def download_history_item_snapshot(
    job: DownloadJobRow,
    inspection: MediaInspectionRow,
    selected_format: MediaFormatRow,
    artifact: ArtifactRow | None,
    now: datetime,
) -> DownloadHistoryItemSnapshot:
    metadata = dict(inspection.metadata_json)
    thumbnail = metadata.get("thumbnail_url")
    return DownloadHistoryItemSnapshot(
        id=job.id,
        title=inspection.title,
        thumbnail_url=thumbnail if isinstance(thumbnail, str) else None,
        format_name=selected_format.display_name,
        status=job.status,
        progress=job.progress,
        error_code=job.error_code,
        created_at=as_utc(job.created_at),
        updated_at=as_utc(job.updated_at),
        finished_at=None if job.finished_at is None else as_utc(job.finished_at),
        file_available=(
            job.status == "succeeded"
            and artifact is not None
            and artifact.deleted_at is None
            and as_utc(artifact.expires_at) > as_utc(now)
        ),
        file_expires_at=(None if artifact is None else as_utc(artifact.expires_at)),
    )


def download_history_page_snapshot(
    items: tuple[DownloadHistoryItemSnapshot, ...],
    *,
    page: int,
    page_size: int,
    total: int,
    counts: dict[str, int],
) -> DownloadHistoryPageSnapshot:
    return DownloadHistoryPageSnapshot(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        summary=DownloadHistorySummarySnapshot(
            total=sum(counts.values()),
            succeeded=counts.get("succeeded", 0),
            active=sum(
                counts.get(value, 0) for value in ("queued", "running", "retry_wait")
            ),
            failed=counts.get("failed", 0),
        ),
    )


def artifact_snapshot(row: ArtifactRow) -> ArtifactSnapshot:
    return ArtifactSnapshot(
        id=row.id,
        job_id=row.job_id,
        attempt=row.attempt,
        bucket=row.bucket,
        object_key=row.object_key,
        sha256=row.sha256,
        size_bytes=row.size_bytes,
        duration_ms=row.duration_ms,
        container=row.container,
        content_type=row.content_type,
        media_metadata=dict(row.media_metadata),
        expires_at=as_utc(row.expires_at),
    )


def outbox_snapshot(row: OutboxEventRow) -> OutboxSnapshot:
    return OutboxSnapshot(
        id=row.id,
        aggregate_type=row.aggregate_type,
        aggregate_id=row.aggregate_id,
        event_type=row.event_type,
        payload=dict(row.payload),
        publish_attempts=row.publish_attempts,
        available_at=as_utc(row.available_at),
        created_at=as_utc(row.created_at),
    )
