"""Read-only projections for immutable analysis inputs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from app.application.analysis import (
    AnalysisArtifactSnapshot,
    AnalysisDocumentSnapshot,
)
from app.application.analysis_execution import (
    AnalysisScreenplaySource,
    ScreenplaySceneSource,
)
from app.infrastructure.analysis_repository_mapping import analysis_artifact_snapshot
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import (
    ArtifactRow,
    DocumentArtifactRow,
    DocumentRow,
    DownloadJobRow,
)


class AnalysisInputRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def get_artifact_for_download(
        self, download_id: UUID
    ) -> AnalysisArtifactSnapshot | None:
        return await self._artifact_projection(ArtifactRow.job_id == download_id)

    async def get_artifact(self, artifact_id: UUID) -> AnalysisArtifactSnapshot | None:
        return await self._artifact_projection(ArtifactRow.id == artifact_id)

    async def _artifact_projection(
        self, criterion: ColumnElement[bool]
    ) -> AnalysisArtifactSnapshot | None:
        async with self._sessions() as session:
            result = (
                await session.execute(
                    select(ArtifactRow, DownloadJobRow)
                    .join(DownloadJobRow, DownloadJobRow.id == ArtifactRow.job_id)
                    .where(criterion, ArtifactRow.deleted_at.is_(None))
                )
            ).one_or_none()
            if result is None:
                return None
            artifact, download = result
            return analysis_artifact_snapshot(artifact, download)

    async def get_document_for_analysis(
        self, document_id: UUID
    ) -> AnalysisDocumentSnapshot | None:
        async with self._sessions() as session:
            result = (
                await session.execute(
                    select(DocumentRow, DocumentArtifactRow)
                    .outerjoin(
                        DocumentArtifactRow,
                        and_(
                            DocumentArtifactRow.document_id == DocumentRow.id,
                            DocumentArtifactRow.kind == "normalized",
                        ),
                    )
                    .where(
                        DocumentRow.id == document_id,
                        DocumentRow.deleted_at.is_(None),
                    )
                )
            ).one_or_none()
            if result is None:
                return None
            document, normalized = result
            return AnalysisDocumentSnapshot(
                id=document.id,
                owner_hash=document.owner_hash,
                status=document.status,
                text_sha256=document.text_sha256,
                expires_at=(
                    None if document.expires_at is None else as_utc(document.expires_at)
                ),
                normalized_status=None if normalized is None else normalized.status,
                normalized_sha256=None if normalized is None else normalized.sha256,
                normalized_expires_at=(
                    None if normalized is None else as_utc(normalized.expires_at)
                ),
            )

    async def get_screenplay_source(
        self, document_id: UUID, now: datetime
    ) -> AnalysisScreenplaySource | None:
        async with self._sessions() as session:
            result = (
                await session.execute(
                    select(DocumentRow, DocumentArtifactRow)
                    .join(
                        DocumentArtifactRow,
                        DocumentArtifactRow.document_id == DocumentRow.id,
                    )
                    .where(
                        DocumentRow.id == document_id,
                        DocumentRow.status == "ready",
                        DocumentRow.deleted_at.is_(None),
                        DocumentRow.expires_at > now,
                        DocumentArtifactRow.kind == "normalized",
                        DocumentArtifactRow.status == "ready",
                        DocumentArtifactRow.deleted_at.is_(None),
                        DocumentArtifactRow.expires_at > now,
                    )
                )
            ).one_or_none()
            if result is None:
                return None
            document, artifact = result
            if (
                document.character_count is None
                or document.detected_language is None
                or artifact.content_type != "text/markdown; charset=utf-8"
            ):
                raise ValueError("screenplay source metadata is incomplete")
            return AnalysisScreenplaySource(
                artifact_id=artifact.id,
                document_id=document.id,
                owner_hash=document.owner_hash,
                bucket=artifact.bucket,
                object_key=artifact.object_key,
                sha256=artifact.sha256,
                size_bytes=artifact.size_bytes,
                character_count=document.character_count,
                detected_language=document.detected_language,
                expires_at=min(
                    as_utc(document.expires_at), as_utc(artifact.expires_at)
                ),
                scenes=_screenplay_scenes(artifact.artifact_metadata),
            )


def _screenplay_scenes(metadata: object) -> tuple[ScreenplaySceneSource, ...]:
    if not isinstance(metadata, dict) or set(metadata) != {"scenes"}:
        raise ValueError("screenplay artifact metadata is invalid")
    values = metadata["scenes"]
    if not isinstance(values, list):
        raise ValueError("screenplay scene metadata is invalid")
    scenes: list[ScreenplaySceneSource] = []
    for value in values:
        if not isinstance(value, dict) or set(value) != {
            "id",
            "start",
            "end",
            "elements",
        }:
            raise ValueError("screenplay scene metadata is invalid")
        if not isinstance(value["elements"], list):
            raise ValueError("screenplay element metadata is invalid")
        scenes.append(
            ScreenplaySceneSource(
                id=value["id"],
                start=value["start"],
                end=value["end"],
            )
        )
    return tuple(scenes)
