"""Validate every persisted fact required for Provider analysis release."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.application.downloads import EncryptedUrl
from app.application.provider_analysis_canary import (
    AnalysisCanaryEvidence,
    AnalysisCanaryObject,
)
from app.domain.analysis import VideoAnalysisResult
from app.domain.providers import ProviderAccessContextRef
from app.infrastructure.analysis_repository_serialization import (
    analysis_result_from_document,
)
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import (
    AnalysisJobRow,
    AnalysisReportArtifactRow,
    AnalysisReportVersionRow,
    AnalysisRunRow,
    ArtifactRow,
    DownloadJobRow,
    MediaInspectionRow,
    TaskEventRow,
)


def validated_evidence(
    job: AnalysisJobRow,
    run: AnalysisRunRow,
    report: AnalysisReportVersionRow,
    artifact: ArtifactRow,
    download: DownloadJobRow,
    inspection: MediaInspectionRow,
    report_files: tuple[AnalysisReportArtifactRow, ...],
    event: TaskEventRow | None,
    *,
    now: datetime,
    bucket: str,
) -> AnalysisCanaryEvidence | None:
    files = {
        item.format
        for item in report_files
        if item.status == "available"
        and item.deleted_at is None
        and item.bucket == bucket
        and item.size_bytes > 0
    }
    payload = {} if event is None else event.payload
    if not (
        job.status == run.status == "succeeded"
        and job.progress == run.progress == 100
        and job.deleted_at is None
        and job.current_report_id == report.id
        and job.active_run_id == report.run_id == run.id
        and report.status == "available"
        and report.published_at is not None
        and as_utc(report.published_at) >= as_utc(now) - timedelta(days=7)
        and bool(report.report_markdown.strip())
        and job.input_sha256 == report.input_sha256 == artifact.sha256
        and artifact.bucket == bucket
        and artifact.deleted_at is None
        and artifact.size_bytes > 0
        and artifact.duration_ms > 0
        and _has_stream(artifact.media_metadata, "video_streams")
        and _has_stream(artifact.media_metadata, "audio_streams")
        and download.status == "succeeded"
        and download.progress == 100
        and files == {"markdown", "docx"}
        and report.provider == run.provider
        and report.model == run.model
        and report.cli_version == run.cli_version
        and all((report.provider, report.model, report.cli_version))
        and payload.get("task_id") == str(job.id)
        and payload.get("run_id") == str(run.id)
        and payload.get("status") == "succeeded"
        and payload.get("report_status") == "available"
    ):
        return None
    try:
        result = analysis_result_from_document(report.result_json)
        context = ProviderAccessContextRef.from_document(
            inspection.metadata_json.get("provider_access_context")
        )
        source = EncryptedUrl(
            inspection.url_ciphertext,
            inspection.url_nonce,
            inspection.url_key_id,
        )
    except (TypeError, ValueError):
        return None
    if (
        not isinstance(result, VideoAnalysisResult)
        or result.media.duration_ms != artifact.duration_ms
        or result.media.size_bytes != artifact.size_bytes
        or result.media.container != artifact.container
    ):
        return None
    objects = (
        AnalysisCanaryObject(artifact.object_key, artifact.size_bytes, artifact.sha256),
        *tuple(
            AnalysisCanaryObject(item.object_key, item.size_bytes, item.sha256)
            for item in report_files
            if item.format in files
        ),
    )
    if len(objects) != 3:
        return None
    return AnalysisCanaryEvidence(
        source,
        context,
        as_utc(report.published_at),
        objects,
    )


def _has_stream(metadata: dict[str, object], name: str) -> bool:
    value = metadata.get(name)
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1
