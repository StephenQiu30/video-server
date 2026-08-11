from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.domain.analysis import AnalysisMedia, parse_analysis_result
from app.domain.providers import ProviderAccessContextRef, ProviderAccessMode
from app.infrastructure.analysis_repository_serialization import (
    analysis_result_document,
)
from app.infrastructure.database import Base, create_session_factory
from app.infrastructure.database.models import (
    AnalysisJobRow,
    AnalysisReportArtifactRow,
    AnalysisReportVersionRow,
    AnalysisRunRow,
    ArtifactRow,
    DownloadJobRow,
    MediaFormatRow,
    MediaInspectionRow,
    TaskEventRow,
)
from app.infrastructure.provider_analysis_evidence import (
    SqlAlchemyAnalysisCanaryEvidenceReader,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from tests.unit.workers.analysis.fixtures import valid_mapping

NOW = datetime(2026, 8, 11, 6, tzinfo=UTC)


@pytest.mark.asyncio
async def test_reads_only_complete_download_agent_report_and_realtime_chain() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    job_id = await _seed_complete_chain(sessions)
    reader = SqlAlchemyAnalysisCanaryEvidenceReader(sessions, bucket="video-artifacts")

    evidence = await reader.get(job_id, now=NOW)

    assert evidence is not None
    assert evidence.access_context.provider_key == "acfun"
    assert evidence.source_url.ciphertext == b"ciphertext"
    assert len(evidence.objects) == 3

    async with sessions() as session, session.begin():
        docx = await session.scalar(
            select(AnalysisReportArtifactRow).where(
                AnalysisReportArtifactRow.format == "docx"
            )
        )
        assert docx is not None
        docx.status = "failed"
    assert await reader.get(job_id, now=NOW) is None
    await engine.dispose()


async def _seed_complete_chain(sessions) -> object:
    inspection_id, format_id, download_id, artifact_id = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    job_id, run_id, report_id = uuid4(), uuid4(), uuid4()
    expiry = NOW + timedelta(days=1)
    context = ProviderAccessContextRef(
        provider_key="acfun",
        profile_version="acfun-public-v1",
        access_mode=ProviderAccessMode.ANONYMOUS,
        credential_version_id=None,
        egress_affinity_id="default",
        client_profile_id="yt-dlp-default",
        attestation_provider_version=None,
        engine_commit="5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc",
    )
    result = parse_analysis_result(
        valid_mapping(),
        AnalysisMedia(duration_ms=2_000, container="mp4", size_bytes=1_024),
        expected_language="zh-CN",
    )
    async with sessions() as session, session.begin():
        inspection = MediaInspectionRow(
            id=inspection_id,
            owner_hash="a" * 64,
            idempotency_key="inspection-key",
            request_fingerprint="i" * 64,
            url_ciphertext=b"ciphertext",
            url_nonce=b"nonce",
            url_key_id="fernet-v1",
            extractor_key="AcFunVideo",
            provider_media_id="35457073",
            title="Fixture",
            duration_seconds=2,
            metadata_json={"provider_access_context": context.to_document()},
            expires_at=expiry,
            created_at=NOW,
        )
        session.add(inspection)
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
                created_at=NOW,
            )
        )
        await session.flush()
        session.add(
            DownloadJobRow(
                id=download_id,
                inspection_id=inspection_id,
                format_id=format_id,
                owner_hash="a" * 64,
                idempotency_key="download-key",
                request_fingerprint="d" * 64,
                semantic_plan={"height": 720},
                status="succeeded",
                progress=100,
                attempt=1,
                finished_at=NOW,
                created_at=NOW,
                updated_at=NOW,
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
                sha256="b" * 64,
                size_bytes=1_024,
                duration_ms=2_000,
                container="mp4",
                content_type="video/mp4",
                media_metadata={"video_streams": 1, "audio_streams": 1},
                expires_at=expiry,
                created_at=NOW,
            )
        )
        await session.flush()
        session.add(
            AnalysisJobRow(
                id=job_id,
                artifact_id=artifact_id,
                owner_hash="a" * 64,
                idempotency_key="analysis-key",
                request_fingerprint="q" * 64,
                input_sha256="b" * 64,
                skill_id="director-breakdown",
                skill_instructions="complete video",
                output_language="zh-CN",
                status="succeeded",
                progress=100,
                attempt=1,
                version=4,
                active_run_id=run_id,
                current_report_id=report_id,
                current_run_no=1,
                finished_at=NOW,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        session.add(
            AnalysisRunRow(
                id=run_id,
                job_id=job_id,
                run_no=1,
                trigger="initial",
                status="succeeded",
                progress=100,
                attempt=1,
                version=4,
                started_at=NOW - timedelta(minutes=1),
                finished_at=NOW,
                provider="codex",
                model="gpt-5.6-sol",
                cli_version="1.0.0",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        session.add(
            AnalysisReportVersionRow(
                id=report_id,
                job_id=job_id,
                run_id=run_id,
                input_sha256="b" * 64,
                language="zh-CN",
                result_json=analysis_result_document(result),
                report_markdown="# report",
                content_sha256="c" * 64,
                renderer_version="analysis-report-v1",
                provider="codex",
                model="gpt-5.6-sol",
                cli_version="1.0.0",
                status="available",
                attempt=1,
                created_at=NOW,
                published_at=NOW,
            )
        )
        await session.flush()
        for report_format in ("markdown", "docx"):
            session.add(
                AnalysisReportArtifactRow(
                    report_id=report_id,
                    format=report_format,
                    bucket="video-artifacts",
                    object_key=f"reports/{report_id}/report.{report_format}",
                    content_type="application/octet-stream",
                    size_bytes=100,
                    sha256=("d" if report_format == "markdown" else "e") * 64,
                    status="available",
                    created_at=NOW,
                    available_at=NOW,
                    expires_at=expiry,
                )
            )
        session.add(
            TaskEventRow(
                owner_hash="a" * 64,
                task_type="analysis",
                task_id=job_id,
                run_id=run_id,
                run_no=1,
                version=4,
                event_type="task.updated",
                payload={
                    "task_id": str(job_id),
                    "run_id": str(run_id),
                    "status": "succeeded",
                    "report_status": "available",
                },
                occurred_at=NOW,
            )
        )
    return job_id
