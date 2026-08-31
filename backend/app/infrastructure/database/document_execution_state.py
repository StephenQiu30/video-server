from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.import_execution import (
    ImportVerificationClaim,
    VerifiedDocumentImport,
)
from app.application.imports import ImportPersistenceConflict
from app.domain.imports import ImportErrorCode, ImportStatus

from .document_execution_artifacts import artifact_row, artifacts_match
from .document_execution_support import (
    artifact_keys,
    clear_lease,
    lock_attempt,
    lock_document,
    owns,
    validate_artifact,
)
from .models import DocumentArtifactRow

_FAILURE_CODES = {
    ImportErrorCode.SIZE_MISMATCH,
    ImportErrorCode.SHA256_MISMATCH,
    ImportErrorCode.DOCUMENT_FORMAT_UNSUPPORTED,
    ImportErrorCode.DOCUMENT_ENCRYPTED,
    ImportErrorCode.DOCUMENT_ARCHIVE_UNSAFE,
    ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE,
    ImportErrorCode.DOCUMENT_STRUCTURE_INVALID,
}


async def complete_verification(
    sessions: async_sessionmaker[AsyncSession],
    claim: ImportVerificationClaim,
    artifact: VerifiedDocumentImport,
    *,
    worker_id: str,
    bucket: str,
    now: datetime,
) -> None:
    validate_artifact(claim, artifact, bucket)
    original_key, normalized_key = artifact_keys(claim)
    async with sessions() as session, session.begin():
        row = await lock_document(session, claim.resource_id)
        if row.status == ImportStatus.READY.value:
            stored = tuple(
                (
                    await session.scalars(
                        select(DocumentArtifactRow).where(
                            DocumentArtifactRow.document_id == row.id
                        )
                    )
                ).all()
            )
            if not artifacts_match(
                stored, artifact, bucket, original_key, normalized_key
            ):
                raise ImportPersistenceConflict(
                    "completed document artifacts are inconsistent"
                )
            return
        current = await lock_attempt(session, row.id, claim.attempt)
        if (
            row.status != ImportStatus.VERIFYING.value
            or row.attempt != claim.attempt
            or row.version != claim.version
            or current.status != ImportStatus.VERIFYING.value
            or not owns(current, worker_id, now)
        ):
            raise ImportPersistenceConflict("document verification lease was lost")
        session.add_all(
            [
                artifact_row(
                    claim.resource_id,
                    "original",
                    bucket,
                    original_key,
                    artifact.original_content_type,
                    artifact.original_size_bytes,
                    artifact.original_sha256,
                    {"source_format": claim.source_format.value},
                    now,
                ),
                artifact_row(
                    claim.resource_id,
                    "normalized",
                    bucket,
                    normalized_key,
                    "text/markdown; charset=utf-8",
                    artifact.normalized_size_bytes,
                    artifact.normalized_sha256,
                    {
                        "parse_summary": {
                            "page_count": artifact.parse_summary.page_count,
                            "paragraph_count": artifact.parse_summary.paragraph_count,
                            "heading_count": artifact.parse_summary.heading_count,
                            "list_item_count": artifact.parse_summary.list_item_count,
                            "table_count": artifact.parse_summary.table_count,
                            "dialogue_block_count": (
                                artifact.parse_summary.dialogue_block_count
                            ),
                        },
                        "scenes": [
                            {
                                "id": scene.id,
                                "start": scene.start,
                                "end": scene.end,
                                "elements": [
                                    {
                                        "kind": element.kind.value,
                                        "start": element.start,
                                        "end": element.end,
                                    }
                                    for element in scene.elements
                                ],
                            }
                            for scene in artifact.scenes
                        ],
                    },
                    now,
                ),
            ]
        )
        current.status = ImportStatus.READY.value
        current.error_code = None
        current.finished_at = now
        current.updated_at = now
        clear_lease(current, now)
        row.status = ImportStatus.READY.value
        row.error_code = None
        row.detected_language = artifact.detected_language
        row.scene_count = len(artifact.scenes)
        row.character_count = artifact.character_count
        row.text_sha256 = artifact.normalized_sha256
        row.quality_warnings = list(artifact.quality_warnings)
        row.finished_at = now
        row.version += 1
        row.updated_at = now
        await session.flush()


async def fail_verification(
    sessions: async_sessionmaker[AsyncSession],
    claim: ImportVerificationClaim,
    error_code: ImportErrorCode,
    *,
    worker_id: str,
    now: datetime,
) -> None:
    if error_code not in _FAILURE_CODES:
        raise ValueError("unsupported terminal document verification error")
    async with sessions() as session, session.begin():
        row = await lock_document(session, claim.resource_id)
        if (
            row.status == ImportStatus.FAILED.value
            and row.error_code == error_code.value
        ):
            return
        current = await lock_attempt(session, row.id, claim.attempt)
        if (
            row.status != ImportStatus.VERIFYING.value
            or row.attempt != claim.attempt
            or row.version != claim.version
            or current.status != ImportStatus.VERIFYING.value
            or not owns(current, worker_id, now)
        ):
            raise ImportPersistenceConflict("document verification lease was lost")
        current.status = ImportStatus.FAILED.value
        current.error_code = error_code.value
        current.finished_at = now
        current.updated_at = now
        clear_lease(current, now)
        row.status = ImportStatus.FAILED.value
        row.error_code = error_code.value
        row.finished_at = now
        row.version += 1
        row.updated_at = now
        await session.flush()


async def expected_artifact_object_keys(
    sessions: async_sessionmaker[AsyncSession],
) -> frozenset[str]:
    async with sessions() as session:
        keys = await session.scalars(
            select(DocumentArtifactRow.object_key).where(
                DocumentArtifactRow.status != "deleted"
            )
        )
        return frozenset(keys)
