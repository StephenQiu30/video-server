from __future__ import annotations

from app.application.downloads.download_models import (
    ArtifactSnapshot,
    DownloadPresentationSnapshot,
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
from app.application.downloads.thumbnail import (
    safe_thumbnail_data_url,
    thumbnail_resource_url,
)
from app.domain.downloads import (
    DownloadErrorCode,
    DownloadSourceKind,
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
    thumbnail_available = snapshot.thumbnail_available or (
        safe_thumbnail_data_url(snapshot.metadata.get("thumbnail_url")) is not None
    )
    return InspectionView(
        id=snapshot.id,
        extractor_key=snapshot.extractor_key,
        provider_media_id=snapshot.provider_media_id,
        title=snapshot.title,
        duration_seconds=snapshot.duration_seconds,
        expires_at=snapshot.expires_at,
        formats=formats,
        thumbnail_url=(
            thumbnail_resource_url(snapshot.id) if thumbnail_available else None
        ),
    )


def download_view(
    snapshot: JobSnapshot,
    artifact: ArtifactSnapshot | None = None,
    presentation: DownloadPresentationSnapshot | None = None,
) -> DownloadView:
    try:
        status = DownloadStatus(snapshot.status)
        source_kind = DownloadSourceKind(snapshot.source_kind)
        stage = DownloadStage(snapshot.stage) if snapshot.stage is not None else None
        error = (
            DownloadErrorCode(snapshot.error_code)
            if snapshot.error_code is not None
            else None
        )
    except ValueError as exc:
        raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR) from exc
    format_plan = None
    if source_kind is DownloadSourceKind.REMOTE_PROVIDER:
        try:
            format_plan = public_plan(plan_from_documents(snapshot.semantic_plan, {}))
        except (TypeError, ValueError) as exc:
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
        version=snapshot.version,
        title=None if presentation is None else presentation.title,
        extractor_key=None if presentation is None else presentation.extractor_key,
        duration_seconds=(
            None if presentation is None else presentation.duration_seconds
        ),
        thumbnail_url=(
            thumbnail_resource_url(snapshot.inspection_id)
            if presentation is not None
            and presentation.thumbnail_available
            and snapshot.inspection_id is not None
            else None
        ),
        format_plan=format_plan,
        source_kind=source_kind,
        source_label=(
            "本地视频上传"
            if source_kind is DownloadSourceKind.BROWSER_IMPORT
            else (
                presentation.extractor_key if presentation is not None else "链接下载"
            )
        ),
    )
