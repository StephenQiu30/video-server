from __future__ import annotations

from app.application.imports import ImportApplicationError, ImportApplicationErrorCode
from app.domain.imports import ImportErrorCode, ImportSourceFormat, ImportStatus

from .models import DocumentPage, DocumentPageSnapshot, DocumentSnapshot, DocumentView


def document_page(snapshot: DocumentPageSnapshot, owner_hash: str) -> DocumentPage:
    if snapshot.page < 1 or snapshot.page_size < 1 or snapshot.total < 0:
        raise ImportApplicationError(ImportApplicationErrorCode.INTERNAL_ERROR)
    if any(item.owner_hash != owner_hash for item in snapshot.items):
        raise ImportApplicationError(ImportApplicationErrorCode.INTERNAL_ERROR)
    return DocumentPage(
        items=tuple(document_view(item) for item in snapshot.items),
        page=snapshot.page,
        page_size=snapshot.page_size,
        total=snapshot.total,
    )


def document_view(
    snapshot: DocumentSnapshot,
    *,
    preview: str | None = None,
    preview_truncated: bool = False,
) -> DocumentView:
    try:
        source_format = ImportSourceFormat(snapshot.source_format)
        status = ImportStatus(snapshot.status)
        error_code = (
            None
            if snapshot.error_code is None
            else ImportErrorCode(snapshot.error_code)
        )
    except ValueError as error:
        raise ImportApplicationError(
            ImportApplicationErrorCode.INTERNAL_ERROR
        ) from error
    if source_format.content_kind.value != "screenplay":
        raise ImportApplicationError(ImportApplicationErrorCode.INTERNAL_ERROR)
    return DocumentView(
        id=snapshot.id,
        title=snapshot.title,
        original_filename=snapshot.original_filename,
        source_format=source_format,
        declared_size_bytes=snapshot.declared_size_bytes,
        status=status,
        attempt=snapshot.attempt,
        error_code=error_code,
        version=snapshot.version,
        detected_language=snapshot.detected_language,
        scene_count=snapshot.scene_count,
        character_count=snapshot.character_count,
        quality_warnings=snapshot.quality_warnings,
        parse_summary=snapshot.parse_summary,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
        finished_at=snapshot.finished_at,
        preview=preview,
        preview_truncated=preview_truncated,
    )
