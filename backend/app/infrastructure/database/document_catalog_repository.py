"""Owner-scoped list and detail reads for screenplay documents."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.application.documents import (
    DocumentPageSnapshot,
    DocumentSnapshot,
    DocumentTextArtifactSnapshot,
)

from .base import as_utc
from .models import DocumentArtifactRow, DocumentRow
from .repository_base import RepositoryBase


class SqlAlchemyDocumentCatalogRepository(RepositoryBase):
    async def get_document(
        self, document_id: UUID, owner_hash: str
    ) -> DocumentSnapshot | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(DocumentRow).where(
                    DocumentRow.id == document_id,
                    DocumentRow.owner_hash == owner_hash,
                    DocumentRow.deleted_at.is_(None),
                )
            )
            if row is None:
                return None
            artifact = await session.scalar(
                select(DocumentArtifactRow).where(
                    DocumentArtifactRow.document_id == row.id,
                    DocumentArtifactRow.kind == "normalized",
                    DocumentArtifactRow.status == "ready",
                )
            )
            return _snapshot(row, artifact)

    async def list_documents(
        self, owner_hash: str, *, page: int, page_size: int
    ) -> DocumentPageSnapshot:
        filters = (
            DocumentRow.owner_hash == owner_hash,
            DocumentRow.deleted_at.is_(None),
        )
        async with self._sessions() as session:
            total = await session.scalar(
                select(func.count(DocumentRow.id)).where(*filters)
            )
            rows = await session.scalars(
                select(DocumentRow)
                .where(*filters)
                .order_by(DocumentRow.created_at.desc(), DocumentRow.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            return DocumentPageSnapshot(
                items=tuple(_snapshot(row) for row in rows),
                page=page,
                page_size=page_size,
                total=int(total or 0),
            )


def _snapshot(
    row: DocumentRow, artifact: DocumentArtifactRow | None = None
) -> DocumentSnapshot:
    return DocumentSnapshot(
        id=row.id,
        owner_hash=row.owner_hash,
        title=row.title,
        original_filename=row.original_filename,
        source_format=row.source_format,
        declared_size_bytes=row.declared_size_bytes,
        status=row.status,
        attempt=row.attempt,
        error_code=row.error_code,
        version=row.version,
        detected_language=row.detected_language,
        scene_count=row.scene_count,
        character_count=row.character_count,
        text_sha256=row.text_sha256,
        quality_warnings=tuple(row.quality_warnings),
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
        finished_at=None if row.finished_at is None else as_utc(row.finished_at),
        normalized_artifact=(
            None
            if artifact is None
            else DocumentTextArtifactSnapshot(
                bucket=artifact.bucket,
                object_key=artifact.object_key,
                size_bytes=artifact.size_bytes,
                sha256=artifact.sha256,
            )
        ),
    )
