"""Composition root for the API process."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.dependencies import AnalysisUseCases, DownloadUseCases
from app.application.analysis import CancelAnalysis, CreateAnalysis, GetAnalysis
from app.application.downloads import (
    CancelDownload,
    CreateDownload,
    GetDownload,
    GetDownloadHistory,
    GetInspection,
    HmacRequestFingerprinter,
    InspectMedia,
    IssueDownloadUrl,
)
from app.core.config import Settings
from app.core.url_cipher import URLCipher
from app.infrastructure.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.database import (
    SqlAlchemyDownloadRepository,
    create_engine,
    create_session_factory,
)
from app.infrastructure.download_store import SqlAlchemyDownloadStore
from app.infrastructure.media_runner import MediaRunnerHttpClient
from app.infrastructure.object_storage import MinioObjectStorage
from app.infrastructure.readiness import RuntimeReadiness, build_runtime_readiness
from app.infrastructure.url_security import FernetUrlEnvelope, MediaUrlValidator


@dataclass(slots=True)
class ApiRuntime:
    use_cases: DownloadUseCases
    analysis_use_cases: AnalysisUseCases
    engine: AsyncEngine
    runner: MediaRunnerHttpClient
    readiness: RuntimeReadiness

    async def close(self) -> None:
        await self.readiness.close()
        await self.runner.close()
        await self.engine.dispose()


def build_api_runtime(settings: Settings) -> ApiRuntime:
    engine = create_engine(settings.database_url)
    sessions = create_session_factory(engine)
    repository = SqlAlchemyDownloadRepository(sessions)
    analysis_repository = SqlAlchemyAnalysisRepository(sessions)
    store = SqlAlchemyDownloadStore(repository)
    runner = MediaRunnerHttpClient(
        base_url=settings.runner_base_url,
        secret=settings.runner_hmac_secret.get_secret_value().encode(),
        workspace_root=settings.runner_workspace_root,
        inspect_timeout_seconds=settings.inspect_timeout_seconds,
        download_timeout_seconds=settings.download_timeout_seconds,
    )
    storage = MinioObjectStorage(settings, enable_public_signing=True)
    clock = _utc_now
    fingerprinter = HmacRequestFingerprinter(
        settings.request_fingerprint_secret.get_secret_value().encode()
    )
    envelope = FernetUrlEnvelope(
        URLCipher(settings.url_encryption_key.get_secret_value().encode()),
        key_id=settings.url_encryption_key_id,
    )
    use_cases = DownloadUseCases(
        inspect_media=InspectMedia(
            repository=store,
            runner=runner,
            url_validator=MediaUrlValidator(),
            url_cipher=envelope,
            fingerprinter=fingerprinter,
            now=clock,
            new_id=uuid4,
            inspection_ttl=timedelta(seconds=settings.inspection_ttl_seconds),
            max_duration_seconds=settings.max_video_duration_seconds,
        ),
        get_inspection=GetInspection(store, now=clock),
        create_download=CreateDownload(
            repository=store,
            fingerprinter=fingerprinter,
            now=clock,
            new_id=uuid4,
            max_attempts=settings.max_download_attempts,
        ),
        get_download=GetDownload(store),
        get_download_history=GetDownloadHistory(store),
        cancel_download=CancelDownload(store, now=clock),
        issue_download_url=IssueDownloadUrl(
            store,
            storage,
            now=clock,
            url_ttl=timedelta(seconds=settings.artifact_download_url_ttl_seconds),
        ),
    )
    analysis_use_cases = AnalysisUseCases(
        create_analysis=CreateAnalysis(
            repository=analysis_repository,
            fingerprinter=fingerprinter,
            now=clock,
            new_id=uuid4,
            max_attempts=settings.max_analysis_attempts,
            schema_version=settings.analysis_schema_version,
        ),
        get_analysis=GetAnalysis(analysis_repository),
        cancel_analysis=CancelAnalysis(analysis_repository, now=clock),
    )
    return ApiRuntime(
        use_cases=use_cases,
        analysis_use_cases=analysis_use_cases,
        engine=engine,
        runner=runner,
        readiness=build_runtime_readiness(settings, engine),
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)
