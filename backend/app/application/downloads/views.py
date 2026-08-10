from __future__ import annotations

from app.application.downloads.download_models import (
    ArtifactSnapshot,
    DownloadView,
    JobSnapshot,
)
from app.application.downloads.errors import (
    ApplicationError,
    ApplicationErrorCode,
)
from app.application.downloads.inspection_models import (
    FormatView,
    InspectionSnapshot,
    InspectionView,
)
from app.application.downloads.plans import plan_from_documents, public_plan
from app.domain.downloads import (
    DownloadErrorCode,
    DownloadStage,
    DownloadStatus,
)


def inspection_view(snapshot: InspectionSnapshot) -> InspectionView:
    try:
        formats = tuple(
            FormatView(
                id=item.id,
                display_name=item.display_name,
                plan=public_plan(
                    plan_from_documents(item.semantic_plan, item.provider_hints)
                ),
            )
            for item in snapshot.formats
        )
    except (TypeError, ValueError) as exc:
        raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR) from exc
    return InspectionView(
        id=snapshot.id,
        extractor_key=snapshot.extractor_key,
        provider_media_id=snapshot.provider_media_id,
        title=snapshot.title,
        duration_seconds=snapshot.duration_seconds,
        expires_at=snapshot.expires_at,
        formats=formats,
        thumbnail_url=_thumbnail_url(snapshot.metadata),
    )


def _thumbnail_url(metadata: dict[str, object]) -> str | None:
    value = metadata.get("thumbnail_url")
    if not isinstance(value, str) or len(value) > 2_100_000:
        return None
    allowed_prefixes = (
        "data:image/jpeg;base64,",
        "data:image/png;base64,",
        "data:image/webp;base64,",
    )
    return value if value.startswith(allowed_prefixes) else None


def download_view(
    snapshot: JobSnapshot, artifact: ArtifactSnapshot | None = None
) -> DownloadView:
    try:
        status = DownloadStatus(snapshot.status)
        stage = DownloadStage(snapshot.stage) if snapshot.stage is not None else None
        error = (
            DownloadErrorCode(snapshot.error_code)
            if snapshot.error_code is not None
            else None
        )
    except ValueError as exc:
        raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR) from exc
    return DownloadView(
        id=snapshot.id,
        inspection_id=snapshot.inspection_id,
        format_id=snapshot.format_id,
        status=status,
        stage=stage,
        progress=snapshot.progress,
        attempt=snapshot.attempt,
        error_code=error,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
        finished_at=snapshot.finished_at,
        file_available=artifact is not None,
        file_expires_at=None if artifact is None else artifact.expires_at,
    )
