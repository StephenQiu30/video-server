from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.application.analysis import AnalysisCreate
from app.domain.analysis import AnalysisInputKind, AnalysisResultContract
from app.infrastructure.database.models import DocumentArtifactRow, DocumentRow
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.unit.infrastructure.analysis.factories import OWNER


@dataclass(frozen=True, slots=True)
class ScreenplaySeed:
    document_id: UUID
    owner_hash: str
    sha256: str
    expires_at: datetime


async def seed_screenplay(
    sessions: async_sessionmaker[AsyncSession],
    now: datetime,
    *,
    owner_hash: str = OWNER,
    status: str = "ready",
    sha256: str = "d" * 64,
    expires_at: datetime | None = None,
    normalized_status: str | None = "ready",
) -> ScreenplaySeed:
    document_id = uuid4()
    expiry = expires_at or now + timedelta(hours=1)
    async with sessions() as session, session.begin():
        session.add(
            DocumentRow(
                id=document_id,
                owner_hash=owner_hash,
                idempotency_key=str(uuid4()),
                request_fingerprint="f" * 64,
                title="受控剧本",
                original_filename="controlled.fountain",
                source_format="fountain",
                content_type="text/plain",
                declared_size_bytes=128,
                declared_sha256="e" * 64,
                rights_statement_version="rights-v1",
                status=status,
                attempt=1,
                version=1,
                detected_language="zh-CN",
                scene_count=1,
                character_count=64,
                text_sha256=sha256,
                quality_warnings=[],
                expires_at=expiry,
                finished_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
        if normalized_status is not None:
            session.add(
                DocumentArtifactRow(
                    id=uuid4(),
                    document_id=document_id,
                    kind="normalized",
                    bucket="video-artifacts",
                    object_key=f"documents/{document_id}/1/screenplay.md",
                    content_type="text/markdown; charset=utf-8",
                    size_bytes=64,
                    sha256=sha256,
                    status=normalized_status,
                    artifact_metadata={"attempt": 1},
                    expires_at=expiry,
                    created_at=now,
                    updated_at=now,
                )
            )
    return ScreenplaySeed(document_id, owner_hash, sha256, expiry)


def screenplay_command(
    source: ScreenplaySeed,
    *,
    result_contract: AnalysisResultContract = (
        AnalysisResultContract.SCREENPLAY_ANALYSIS
    ),
) -> AnalysisCreate:
    return AnalysisCreate(
        id=uuid4(),
        run_id=uuid4(),
        artifact_id=None,
        document_id=source.document_id,
        owner_hash=source.owner_hash,
        idempotency_key=f"analysis-{source.document_id}",
        request_fingerprint="a" * 64,
        input_sha256=source.sha256,
        skill_id="screenplay-analysis",
        skill_instructions="受控剧本分析指令",
        skill_instructions_sha256=hashlib.sha256(
            "受控剧本分析指令".encode()
        ).hexdigest(),
        output_language="zh-CN",
        custom_prompt=None,
        max_attempts=3,
        outbox_event_id=uuid4(),
        outbox_event_type="analysis.requested",
        retry_available_until=source.expires_at,
        input_kind=AnalysisInputKind.SCREENPLAY,
        result_contract=result_contract,
    )
