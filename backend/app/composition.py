"""Composition root for the API process."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.dependencies import (
    AnalysisUseCases,
    DocumentImportUseCases,
    DownloadUseCases,
    MediaImportUseCases,
    SourceDiscoveryUseCases,
)
from app.application.ai_providers import AiProviderService
from app.application.analysis import (
    CancelAnalysis,
    CreateAnalysis,
    CreateDocumentAnalysis,
    DeleteAnalysis,
    ExportAnalysisMarkdown,
    ExportAnalysisReport,
    GetAnalysis,
    GetLatestDocumentAnalysis,
    GetLatestDownloadAnalysis,
    ListAnalysisSkills,
    RetryAnalysis,
)
from app.application.auth import AuthService, UserService
from app.application.documents import DeleteDocument, GetDocument, ListDocuments
from app.application.downloads import (
    CancelDownload,
    CreateDownload,
    GetDownload,
    GetDownloadAnalytics,
    GetDownloadHistory,
    GetDownloadThumbnail,
    GetInspection,
    GetThumbnail,
    HmacRequestFingerprinter,
    InspectMedia,
    IssueDownloadUrl,
    PersistThumbnail,
    RetryDownload,
)
from app.application.imports import (
    CancelImport,
    CompleteImportUpload,
    CreateImportResource,
    CreateUploadSession,
    GetImport,
    UploadLimits,
)
from app.application.provider_canaries import ProviderStatusService
from app.application.provider_catalog import ProviderCatalogService
from app.application.source_discoveries import (
    CreateSourceDiscovery,
    GetSourceDiscovery,
    InspectDiscoveredItem,
)
from app.application.storage_files import StorageFileService
from app.core.ai_provider_cipher import FernetAiProviderSecretCipher
from app.core.config import Settings
from app.core.url_cipher import URLCipher
from app.infrastructure.ai_provider_repository import SqlAlchemyAiProviderRepository
from app.infrastructure.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.analysis_skill_catalog import BuiltinAnalysisSkillCatalog
from app.infrastructure.analysis_worker_registry import (
    ANALYSIS_MESSAGE_SCHEMA_VERSION,
    SqlAlchemyAnalysisWorkerRegistry,
)
from app.infrastructure.article_discovery import WeChatArticleDiscoveryAdapter
from app.infrastructure.auth_repository import SqlAlchemyAuthRepository
from app.infrastructure.database import (
    SqlAlchemyDocumentCatalogRepository,
    SqlAlchemyDocumentDeleteRepository,
    SqlAlchemyDocumentImportRepository,
    SqlAlchemyDownloadRepository,
    SqlAlchemyMediaImportRepository,
    SqlAlchemySourceDiscoveryRepository,
    create_engine,
    create_session_factory,
)
from app.infrastructure.download_store import SqlAlchemyDownloadStore
from app.infrastructure.jwt_tokens import JwtTokenService
from app.infrastructure.media_runner import MediaRunnerHttpClient, MediaRunnerRouter
from app.infrastructure.object_storage import MinioObjectStorage
from app.infrastructure.operational_metrics import OperationalMetrics
from app.infrastructure.passwords import Argon2PasswordHasher
from app.infrastructure.provider_canary_repository import (
    SqlAlchemyProviderCanaryRepository,
)
from app.infrastructure.provider_catalog_repository import (
    SqlAlchemyProviderCatalogRepository,
)
from app.infrastructure.provider_status import configured_provider_statuses
from app.infrastructure.provider_status_evidence import (
    MergedProviderStatusEvidenceReader,
    SqlAlchemyDownloadEvidenceReader,
)
from app.infrastructure.rate_limiter import ValkeyRateLimiter
from app.infrastructure.readiness import RuntimeReadiness, build_runtime_readiness
from app.infrastructure.realtime import RabbitMqRealtimeConsumer, RealtimeHub
from app.infrastructure.storage_file_repository import SqlAlchemyStorageFileRepository
from app.infrastructure.task_event_store import TaskEventStore
from app.infrastructure.thumbnail_storage import MinioThumbnailStorage
from app.infrastructure.url_security import FernetUrlEnvelope, MediaUrlValidator
from app.infrastructure.user_repository import SqlAlchemyUserRepository
from app.runner.provider_registry import configure_provider_instances


@dataclass(slots=True)
class ApiRuntime:
    auth_service: AuthService
    user_service: UserService
    use_cases: DownloadUseCases
    analysis_use_cases: AnalysisUseCases
    media_import_use_cases: MediaImportUseCases
    document_import_use_cases: DocumentImportUseCases
    source_discovery_use_cases: SourceDiscoveryUseCases
    engine: AsyncEngine
    runner: MediaRunnerRouter
    rate_limiter: ValkeyRateLimiter | None
    readiness: RuntimeReadiness
    realtime_hub: RealtimeHub
    task_event_store: TaskEventStore
    realtime_consumer: RabbitMqRealtimeConsumer
    operational_metrics: OperationalMetrics
    provider_status_service: ProviderStatusService
    provider_catalog_service: ProviderCatalogService
    ai_provider_service: AiProviderService
    storage_file_service: StorageFileService

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
    configure_provider_instances(settings.peertube_allowed_instances)
    engine = create_engine(settings.database_url)
    sessions = create_session_factory(engine)
    realtime_hub = RealtimeHub(
        max_connections=settings.websocket_max_connections,
        max_per_owner=settings.websocket_max_connections_per_owner,
    )
    repository = SqlAlchemyDownloadRepository(sessions)
    source_discovery_repository = SqlAlchemySourceDiscoveryRepository(sessions)
    media_import_repository = SqlAlchemyMediaImportRepository(sessions)
    document_import_repository = SqlAlchemyDocumentImportRepository(sessions)
    document_catalog_repository = SqlAlchemyDocumentCatalogRepository(sessions)
    document_delete_repository = SqlAlchemyDocumentDeleteRepository(sessions)
    analysis_repository = SqlAlchemyAnalysisRepository(sessions)
    analysis_availability = SqlAlchemyAnalysisWorkerRegistry(
        sessions,
        expected_app_version=settings.app_version,
        expected_message_schema_version=ANALYSIS_MESSAGE_SCHEMA_VERSION,
        stale_after=timedelta(seconds=settings.analysis_worker_stale_seconds),
    )
    auth_repository = SqlAlchemyAuthRepository(sessions)
    user_repository = SqlAlchemyUserRepository(sessions)
    provider_catalog_repository = SqlAlchemyProviderCatalogRepository(sessions)
    ai_provider_repository = SqlAlchemyAiProviderRepository(sessions)
    store = SqlAlchemyDownloadStore(repository)
    anonymous_runner = MediaRunnerHttpClient(
        base_url=settings.runner_base_url,
        secret=settings.runner_hmac_secret.get_secret_value().encode(),
        workspace_root=settings.runner_workspace_root,
        inspect_timeout_seconds=settings.inspect_timeout_seconds,
        download_timeout_seconds=settings.download_timeout_seconds,
    )
    operator_runners = {
        provider: MediaRunnerHttpClient(
            base_url=base_url,
            secret=settings.runner_hmac_secret.get_secret_value().encode(),
            workspace_root=settings.runner_workspace_root,
            inspect_timeout_seconds=settings.inspect_timeout_seconds,
            download_timeout_seconds=settings.download_timeout_seconds,
        )
        for provider, base_url in settings.runner_operator_base_urls.items()
    }
    runner = MediaRunnerRouter(anonymous_runner, operator_runners)
    storage = MinioObjectStorage(settings, enable_public_signing=True)
    import_storage = MinioObjectStorage.for_imports(settings)
    thumbnail_storage = MinioThumbnailStorage(storage)
    persist_thumbnail = PersistThumbnail(store, thumbnail_storage)
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
        bootstrap_admin_secret=settings.auth_bootstrap_admin_secret.get_secret_value(),
    )
    user_service = UserService(repository=user_repository, now=clock)
    provider_baselines = configured_provider_statuses(
        frozenset(settings.runner_operator_base_urls)
    )
    provider_catalog_service = ProviderCatalogService(
        provider_catalog_repository,
        provider_baselines,
        now=clock,
    )
    ai_provider_service = AiProviderService(
        ai_provider_repository,
        FernetAiProviderSecretCipher(
            URLCipher(settings.url_encryption_key.get_secret_value().encode()),
            key_id=settings.url_encryption_key_id,
        ),
        now=clock,
        availability=analysis_availability,
    )
    storage_file_service = StorageFileService(
        SqlAlchemyStorageFileRepository(sessions),
        storage.delete,
        now=clock,
    )
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
        persist_thumbnail=persist_thumbnail,
    )
    inspect_discovered_item = InspectDiscoveredItem(
        source_discovery_repository,
        store,
        fingerprinter,
        now=clock,
        new_id=uuid4,
        inspection_ttl=timedelta(seconds=settings.inspection_ttl_seconds),
    )
    source_discovery_use_cases = SourceDiscoveryUseCases(
        create=CreateSourceDiscovery(
            source_discovery_repository,
            WeChatArticleDiscoveryAdapter(
                timeout_seconds=settings.article_discovery_timeout_seconds,
                max_response_bytes=settings.article_discovery_max_response_bytes,
                max_items=settings.article_discovery_max_items,
                min_interval_seconds=(settings.article_discovery_min_interval_seconds),
                proxy_url=settings.article_discovery_proxy_url,
            ),
            envelope,
            fingerprinter,
            now=clock,
            new_id=uuid4,
            ttl=timedelta(seconds=settings.article_discovery_ttl_seconds),
            max_items=settings.article_discovery_max_items,
        ),
        get=GetSourceDiscovery(source_discovery_repository, now=clock),
    )
    upload_limits = UploadLimits(
        part_size_bytes=settings.import_upload_part_size_bytes,
        max_parts=settings.import_upload_max_parts,
        max_concurrency=settings.import_upload_max_concurrency,
        session_ttl=timedelta(seconds=settings.import_upload_session_ttl_seconds),
    )
    cancel_import = CancelImport(
        media_import_repository,
        import_storage,
        now=clock,
    )
    media_import_use_cases = MediaImportUseCases(
        create_resource=CreateImportResource(
            repository=media_import_repository,
            fingerprinter=fingerprinter,
            now=clock,
            new_id=uuid4,
            media_enabled=settings.media_import_enabled,
            document_enabled=False,
            media_max_bytes=settings.media_import_max_bytes,
            document_max_bytes=settings.document_import_max_bytes,
            rights_statement_version=settings.import_rights_statement_version,
        ),
        create_upload_session=CreateUploadSession(
            media_import_repository,
            import_storage,
            now=clock,
            limits=upload_limits,
        ),
        complete_upload=CompleteImportUpload(
            media_import_repository,
            import_storage,
            now=clock,
        ),
        get_import=GetImport(
            media_import_repository,
            import_storage,
            now=clock,
        ),
        cancel_import=cancel_import,
    )
    document_import_use_cases = DocumentImportUseCases(
        create_resource=CreateImportResource(
            repository=document_import_repository,
            fingerprinter=fingerprinter,
            now=clock,
            new_id=uuid4,
            media_enabled=False,
            document_enabled=settings.document_import_enabled,
            media_max_bytes=settings.media_import_max_bytes,
            document_max_bytes=settings.document_import_max_bytes,
            rights_statement_version=settings.import_rights_statement_version,
        ),
        create_upload_session=CreateUploadSession(
            document_import_repository,
            import_storage,
            now=clock,
            limits=upload_limits,
        ),
        complete_upload=CompleteImportUpload(
            document_import_repository,
            import_storage,
            now=clock,
        ),
        get_import=GetImport(
            document_import_repository,
            import_storage,
            now=clock,
        ),
        cancel_import=CancelImport(
            document_import_repository,
            import_storage,
            now=clock,
        ),
        get_document=GetDocument(
            document_catalog_repository,
            import_storage,
            max_preview_bytes=settings.document_preview_max_bytes,
            max_preview_characters=settings.document_preview_max_characters,
        ),
        list_documents=ListDocuments(document_catalog_repository),
        delete_document=DeleteDocument(
            document_delete_repository,
            import_storage,
            now=clock,
        ),
    )
    use_cases = DownloadUseCases(
        inspect_media=inspect_media,
        inspect_discovered_item=inspect_discovered_item,
        get_inspection=GetInspection(store, now=clock),
        get_thumbnail=GetThumbnail(store, thumbnail_storage, persist_thumbnail),
        get_download_thumbnail=GetDownloadThumbnail(store, thumbnail_storage),
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
        cancel_download=CancelDownload(
            store,
            now=clock,
            browser_import_canceller=cancel_import,
        ),
        retry_download=RetryDownload(
            repository=store,
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
        create_document_analysis=CreateDocumentAnalysis(
            repository=analysis_repository,
            fingerprinter=fingerprinter,
            now=clock,
            new_id=uuid4,
            max_attempts=settings.max_analysis_attempts,
            skill_catalog=skill_catalog,
            enabled=(
                settings.analysis_enabled and settings.screenplay_analysis_enabled
            ),
        ),
        delete_analysis=DeleteAnalysis(analysis_repository, now=clock),
        get_analysis=get_analysis,
        get_latest_download_analysis=GetLatestDownloadAnalysis(
            analysis_repository, get_analysis
        ),
        get_latest_document_analysis=GetLatestDocumentAnalysis(
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
        media_import_use_cases=media_import_use_cases,
        document_import_use_cases=document_import_use_cases,
        source_discovery_use_cases=source_discovery_use_cases,
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
            settings.rabbitmq_url,
            settings.rabbitmq_exchange,
            realtime_hub,
            connection_timeout=settings.rabbitmq_connection_timeout_seconds,
            heartbeat=settings.rabbitmq_heartbeat_seconds,
            reconnect_interval=settings.rabbitmq_reconnect_interval_seconds,
        ),
        operational_metrics=OperationalMetrics(sessions),
        provider_status_service=ProviderStatusService(
            MergedProviderStatusEvidenceReader(
                SqlAlchemyProviderCanaryRepository(sessions),
                SqlAlchemyDownloadEvidenceReader(sessions),
            ),
            provider_baselines,
            now=clock,
            context_reader=runner,
            approved_keys=settings.provider_verified_keys,
            catalog=provider_catalog_repository,
        ),
        provider_catalog_service=provider_catalog_service,
        ai_provider_service=ai_provider_service,
        storage_file_service=storage_file_service,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)
