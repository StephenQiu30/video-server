from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from app.application.import_execution import VerifiedDocumentImport

from .models import DocumentArtifactRow


def artifact_row(
    document_id: UUID,
    kind: str,
    bucket: str,
    object_key: str,
    content_type: str,
    size_bytes: int,
    sha256: str,
    metadata: dict[str, object],
    expires_at: datetime,
    now: datetime,
) -> DocumentArtifactRow:
    return DocumentArtifactRow(
        id=uuid4(),
        document_id=document_id,
        kind=kind,
        bucket=bucket,
        object_key=object_key,
        content_type=content_type,
        size_bytes=size_bytes,
        sha256=sha256,
        status="ready",
        artifact_metadata=metadata,
        expires_at=expires_at,
        created_at=now,
        updated_at=now,
    )


def artifacts_match(
    rows: tuple[DocumentArtifactRow, ...],
    artifact: VerifiedDocumentImport,
    bucket: str,
    original_key: str,
    normalized_key: str,
) -> bool:
    by_kind = {row.kind: row for row in rows}
    original, normalized = by_kind.get("original"), by_kind.get("normalized")
    return bool(
        original
        and normalized
        and original.bucket == normalized.bucket == bucket
        and original.object_key == original_key
        and original.size_bytes == artifact.original_size_bytes
        and original.sha256 == artifact.original_sha256
        and normalized.object_key == normalized_key
        and normalized.size_bytes == artifact.normalized_size_bytes
        and normalized.sha256 == artifact.normalized_sha256
    )
