"""Composition root for the API process."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.dependencies import AnalysisUseCases, DownloadUseCases
from app.application.analysis import (
    CancelAnalysis,
    CreateAnalysis,
    DeleteAnalysis,
    ExportAnalysisMarkdown,
    ExportAnalysisReport,
    GetAnalysis,
    GetLatestDownloadAnalysis,
    ListAnalysisSkills,
    RetryAnalysis,
)
from app.application.auth import AuthService, UserService
from app.application.downloads import (
    CancelDownload,
    CreateDownload,
    GetDownload,
    GetDownloadAnalytics,
    GetDownloadHistory,
    GetInspection,
    HmacRequestFingerprinter,
    InspectMedia,
    IssueDownloadUrl,
    RetryDownload,
)
from app.core.config import Settings
from app.core.url_cipher import URLCipher
from app.infrastructure.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.analysis_skill_catalog import BuiltinAnalysisSkillCatalog
from app.infrastructure.auth_repository import SqlAlchemyAuthRepository
from app.infrastructure.database import (
    SqlAlchemyDownloadRepository,
    create_engine,
    create_session_factory,
)
from app.infrastructure.download_store import SqlAlchemyDownloadStore
from app.infrastructure.jwt_tokens import JwtTokenService
from app.infrastructure.media_runner import MediaRunnerHttpClient, MediaRunnerRouter
from app.infrastructure.object_storage import MinioObjectStorage
from app.infrastructure.operational_metrics import OperationalMetrics
from app.infrastructure.passwords import Argon2PasswordHasher
from app.infrastructure.rate_limiter import ValkeyRateLimiter
from app.infrastructure.readiness import RuntimeReadiness, build_runtime_readiness
from app.infrastructure.realtime import RabbitMqRealtimeConsumer, RealtimeHub
from app.infrastructure.task_event_store import TaskEventStore
from app.infrastructure.url_security import FernetUrlEnvelope, MediaUrlValidator
from app.infrastructure.user_repository import SqlAlchemyUserRepository


@dataclass(slots=True)
class ApiRuntime:
    auth_service: AuthService
    user_service: UserService
    use_cases: DownloadUseCases
    analysis_use_cases: AnalysisUseCases
    engine: AsyncEngine
    runner: MediaRunnerRouter
    rate_limiter: ValkeyRateLimiter | None
    readiness: RuntimeReadiness
    realtime_hub: RealtimeHub
    task_event_store: TaskEventStore
    realtime_consumer: RabbitMqRealtimeConsumer
    operational_metrics: OperationalMetrics

    async def start(self) -> None:
        await self.realtime_consumer.start()

    async def close(self) -> None:
        await self.realtime_consumer.close()
        await self.readiness.close()
        await self.runner.close()
        if self.rate_limiter is not None:
            await self.rate_limiter.close()
        await self.engine.dispose()


def build_api_runtime(settings: Settings) -> ApiRuntime:
    engine = create_engine(settings.database_url)
    sessions = create_session_factory(engine)
    realtime_hub = RealtimeHub(
        max_connections=settings.websocket_max_connections,
        max_per_owner=settings.websocket_max_connections_per_owner,
    )
    repository = SqlAlchemyDownloadRepository(sessions)
    analysis_repository = SqlAlchemyAnalysisRepository(sessions)
    auth_repository = SqlAlchemyAuthRepository(sessions)
    user_repository = SqlAlchemyUserRepository(sessions)
    store = SqlAlchemyDownloadStore(repository)
    anonymous_runner = MediaRunnerHttpClient(
        base_url=settings.runner_base_url,
        secret=settings.runner_hmac_secret.get_secret_value().encode(),
        workspace_root=settings.runner_workspace_root,
        inspect_timeout_seconds=settings.inspect_timeout_seconds,
        download_timeout_seconds=settings.download_timeout_seconds,
    )
    operator_runner = (
        MediaRunnerHttpClient(
            base_url=settings.runner_operator_base_url,
            secret=settings.runner_hmac_secret.get_secret_value().encode(),
            workspace_root=settings.runner_workspace_root,
            inspect_timeout_seconds=settings.inspect_timeout_seconds,
            download_timeout_seconds=settings.download_timeout_seconds,
        )
        if settings.runner_operator_base_url is not None
        else None
    )
    runner = MediaRunnerRouter(anonymous_runner, operator_runner)
    storage = MinioObjectStorage(settings, enable_public_signing=True)
    rate_limiter = (
        ValkeyRateLimiter(
            settings.valkey_url,
            settings.request_fingerprint_secret.get_secret_value().encode(),
        )
        if settings.valkey_url
        else None
    )
    clock = _utc_now
    auth_service = AuthService(
        repository=auth_repository,
        passwords=Argon2PasswordHasher(),
        tokens=JwtTokenService(
            secret=settings.auth_jwt_secret.get_secret_value().encode(),
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
            access_ttl=timedelta(seconds=settings.auth_access_token_ttl_seconds),
            refresh_ttl=timedelta(seconds=settings.auth_refresh_token_ttl_seconds),
        ),
        now=clock,
        new_id=uuid4,
        bootstrap_admin_email=(
            str(settings.auth_bootstrap_admin_email)
            if settings.auth_bootstrap_admin_email is not None
            else None
        ),
    )
    user_service = UserService(repository=user_repository, now=clock)
    fingerprinter = HmacRequestFingerprinter(
        settings.request_fingerprint_secret.get_secret_value().encode()
    )
    envelope = FernetUrlEnvelope(
        URLCipher(settings.url_encryption_key.get_secret_value().encode()),
        key_id=settings.url_encryption_key_id,
    )
    inspect_media = InspectMedia(
        repository=store,
        runner=runner,
        url_validator=MediaUrlValidator(),
        url_cipher=envelope,
        fingerprinter=fingerprinter,
        now=clock,
        new_id=uuid4,
        inspection_ttl=timedelta(seconds=settings.inspection_ttl_seconds),
        max_duration_seconds=settings.max_video_duration_seconds,
    )
    use_cases = DownloadUseCases(
        inspect_media=inspect_media,
        get_inspection=GetInspection(store, now=clock),
        create_download=CreateDownload(
            repository=store,
            fingerprinter=fingerprinter,
            now=clock,
            new_id=uuid4,
            max_attempts=settings.max_download_attempts,
        ),
        get_download=GetDownload(store, now=clock),
        get_download_history=GetDownloadHistory(store, now=clock),
        get_download_analytics=GetDownloadAnalytics(store, now=clock),
        cancel_download=CancelDownload(store, now=clock),
        retry_download=RetryDownload(
            repository=store,
            inspect_media=inspect_media,
            url_cipher=envelope,
            fingerprinter=fingerprinter,
            now=clock,
            new_id=uuid4,
            max_attempts=settings.max_download_attempts,
        ),
        issue_download_url=IssueDownloadUrl(
            store,
            storage,
            now=clock,
            url_ttl=timedelta(seconds=settings.artifact_download_url_ttl_seconds),
        ),
    )
    get_analysis = GetAnalysis(analysis_repository)
    skill_catalog = BuiltinAnalysisSkillCatalog()
    analysis_use_cases = AnalysisUseCases(
        list_analysis_skills=ListAnalysisSkills(skill_catalog),
        create_analysis=CreateAnalysis(
            repository=analysis_repository,
            fingerprinter=fingerprinter,
            now=clock,
            new_id=uuid4,
            max_attempts=settings.max_analysis_attempts,
            skill_catalog=skill_catalog,
            enabled=settings.analysis_enabled,
        ),
        delete_analysis=DeleteAnalysis(analysis_repository, now=clock),
        get_analysis=get_analysis,
        get_latest_download_analysis=GetLatestDownloadAnalysis(
            analysis_repository, get_analysis
        ),
        cancel_analysis=CancelAnalysis(analysis_repository, now=clock),
        retry_analysis=RetryAnalysis(
            analysis_repository,
            now=clock,
            new_id=uuid4,
            max_runs_per_job=settings.analysis_max_runs_per_job,
            min_interval_seconds=(settings.analysis_manual_retry_min_interval_seconds),
            retries_per_day=settings.analysis_manual_retries_per_day,
        ),
        export_analysis_report=ExportAnalysisReport(
            get_analysis, analysis_repository, storage
        ),
        export_analysis_markdown=ExportAnalysisMarkdown(
            get_analysis, analysis_repository, storage
        ),
    )
    return ApiRuntime(
        auth_service=auth_service,
        user_service=user_service,
        use_cases=use_cases,
        analysis_use_cases=analysis_use_cases,
        engine=engine,
        runner=runner,
        rate_limiter=rate_limiter,
        readiness=build_runtime_readiness(
            settings,
            engine,
            valkey_check=rate_limiter.ping if rate_limiter is not None else None,
        ),
        realtime_hub=realtime_hub,
        task_event_store=TaskEventStore(sessions),
        realtime_consumer=RabbitMqRealtimeConsumer(
            settings.rabbitmq_url, settings.rabbitmq_exchange, realtime_hub
        ),
        operational_metrics=OperationalMetrics(sessions),
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)
