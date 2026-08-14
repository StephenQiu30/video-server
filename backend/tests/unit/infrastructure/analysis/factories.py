from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.application.analysis import AnalysisCreate
from app.domain.analysis import (
    AnalysisMedia,
    AnalysisResult,
    parse_analysis_result,
)
from app.infrastructure.database.models import (
    ArtifactRow,
    DownloadJobRow,
    MediaFormatRow,
    MediaInspectionRow,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.unit.workers.analysis.fixtures import valid_mapping

OWNER = "a" * 64


@dataclass(frozen=True, slots=True)
class ArtifactSeed:
    artifact_id: UUID
    download_id: UUID
    owner_hash: str
    sha256: str
    expires_at: datetime


async def seed_artifact(
    sessions: async_sessionmaker[AsyncSession],
    now: datetime,
    *,
    owner_hash: str = OWNER,
    status: str = "succeeded",
    sha256: str = "b" * 64,
    expires_at: datetime | None = None,
) -> ArtifactSeed:
    inspection_id, format_id, download_id, artifact_id = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    expiry = expires_at or now + timedelta(hours=1)
    async with sessions() as session, session.begin():
        session.add(
            MediaInspectionRow(
                id=inspection_id,
                owner_hash=owner_hash,
                idempotency_key=str(uuid4()),
                request_fingerprint="i" * 64,
                url_ciphertext=b"cipher",
                url_nonce=b"nonce",
                url_key_id="primary",
                extractor_key="Controlled",
                provider_media_id=str(uuid4()),
                title="Controlled fixture",
                duration_seconds=30,
                metadata_json={},
                expires_at=expiry,
                created_at=now,
            )
        )
        await session.flush()
        session.add(
            MediaFormatRow(
                id=format_id,
                inspection_id=inspection_id,
                display_name="720p",
                plan_fingerprint="p" * 64,
                semantic_plan={"height": 720},
                provider_hints={},
                expires_at=expiry,
                created_at=now,
            )
        )
        await session.flush()
        session.add(
            DownloadJobRow(
                id=download_id,
                inspection_id=inspection_id,
                format_id=format_id,
                owner_hash=owner_hash,
                idempotency_key=str(uuid4()),
                request_fingerprint="d" * 64,
                semantic_plan={"height": 720},
                status=status,
                progress=100 if status == "succeeded" else 0,
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
        session.add(
            ArtifactRow(
                id=artifact_id,
                job_id=download_id,
                attempt=1,
                bucket="video-artifacts",
                object_key=f"downloads/{download_id}/1/video.mp4",
                sha256=sha256,
                size_bytes=1_024,
                duration_ms=30_000,
                container="mp4",
                content_type="video/mp4",
                media_metadata={},
                expires_at=expiry,
                created_at=now,
            )
        )
    return ArtifactSeed(artifact_id, download_id, owner_hash, sha256, expiry)


def analysis_command(
    source: ArtifactSeed,
    *,
    job_id: UUID | None = None,
    event_id: UUID | None = None,
    idempotency_key: str | None = None,
    fingerprint: str | None = None,
    max_attempts: int = 3,
) -> AnalysisCreate:
    return AnalysisCreate(
        id=job_id or uuid4(),
        run_id=uuid4(),
        artifact_id=source.artifact_id,
        owner_hash=source.owner_hash,
        idempotency_key=idempotency_key or f"analysis-{source.artifact_id}",
        request_fingerprint=fingerprint
        or hashlib.sha256(
            f"{source.artifact_id}:director-breakdown:zh-CN".encode()
        ).hexdigest(),
        input_sha256=source.sha256,
        skill_id="director-breakdown",
        skill_instructions="导演拉片完整指令",
        skill_instructions_sha256=hashlib.sha256(
            "导演拉片完整指令".encode()
        ).hexdigest(),
        output_language="zh-CN",
        custom_prompt=None,
        max_attempts=max_attempts,
        outbox_event_id=event_id or uuid4(),
        outbox_event_type="analysis.requested",
    )


def analysis_result() -> AnalysisResult:
    return parse_analysis_result(
        valid_mapping(),
        AnalysisMedia(duration_ms=2_000, container="mp4", size_bytes=1_024),
        expected_language="zh-CN",
    )
