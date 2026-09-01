"""Request-scoped dependencies shared by API routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Header, Request

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
from app.application.documents import DeleteDocument, GetDocument, ListDocuments
from app.application.downloads import (
    CancelDownload,
    CreateDownload,
    DeleteDownload,
    DownloadArtifactStorage,
    GetDownload,
    GetDownloadAnalytics,
    GetDownloadArtifact,
    GetDownloadHistory,
    GetDownloadThumbnail,
    GetInspection,
    GetThumbnail,
    InspectMedia,
    IssueDownloadUrl,
    RetryDownload,
)
from app.application.imports import (
    CancelImport,
    CompleteImportUpload,
    CreateImportResource,
    CreateUploadSession,
    GetImport,
)
from app.application.provider_canaries import ProviderStatusService
from app.application.provider_catalog import ProviderCatalogService
from app.application.providers import ProviderStatusView
from app.application.source_discoveries import (
    CreateSourceDiscovery,
    GetSourceDiscovery,
    InspectDiscoveredItem,
)
from app.application.storage_files import StorageFileService
from app.core.config import Settings
from app.core.errors import AppError

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="同一业务操作的安全重试必须复用相同键值。",
        examples=["01J4Z3Q9A7M2F6K8P0R1T5V7WX"],
        min_length=1,
        max_length=128,
    ),
]


def get_runtime_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_download_storage(request: Request) -> DownloadArtifactStorage:
    storage = getattr(request.app.state, "download_storage", None)
    if storage is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The download storage service is not available.",
        )
    return cast(DownloadArtifactStorage, storage)


@dataclass(frozen=True, slots=True)
class DownloadUseCases:
    inspect_media: InspectMedia
    inspect_discovered_item: InspectDiscoveredItem
    get_inspection: GetInspection
    get_thumbnail: GetThumbnail
    get_download_thumbnail: GetDownloadThumbnail
    create_download: CreateDownload
    delete_download: DeleteDownload
    get_download: GetDownload
    get_download_artifact: GetDownloadArtifact
    get_download_history: GetDownloadHistory
    get_download_analytics: GetDownloadAnalytics
    cancel_download: CancelDownload
    retry_download: RetryDownload
    issue_download_url: IssueDownloadUrl


@dataclass(frozen=True, slots=True)
class SourceDiscoveryUseCases:
    create: CreateSourceDiscovery
    get: GetSourceDiscovery


@dataclass(frozen=True, slots=True)
class AnalysisUseCases:
    list_analysis_skills: ListAnalysisSkills
    create_analysis: CreateAnalysis
    create_document_analysis: CreateDocumentAnalysis
    delete_analysis: DeleteAnalysis
    get_analysis: GetAnalysis
    get_latest_download_analysis: GetLatestDownloadAnalysis
    get_latest_document_analysis: GetLatestDocumentAnalysis
    cancel_analysis: CancelAnalysis
    retry_analysis: RetryAnalysis
    export_analysis_report: ExportAnalysisReport
    export_analysis_markdown: ExportAnalysisMarkdown


@dataclass(frozen=True, slots=True)
class MediaImportUseCases:
    create_resource: CreateImportResource
    create_upload_session: CreateUploadSession
    complete_upload: CompleteImportUpload
    get_import: GetImport
    cancel_import: CancelImport


@dataclass(frozen=True, slots=True)
class DocumentImportUseCases:
    create_resource: CreateImportResource
    create_upload_session: CreateUploadSession
    complete_upload: CompleteImportUpload
    get_import: GetImport
    cancel_import: CancelImport
    get_document: GetDocument
    list_documents: ListDocuments
    delete_document: DeleteDocument


def get_download_use_cases(request: Request) -> DownloadUseCases:
    container = getattr(request.app.state, "download_use_cases", None)
    if container is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The download service is not available.",
        )
    return cast(DownloadUseCases, container)


def get_source_discovery_use_cases(request: Request) -> SourceDiscoveryUseCases:
    container = getattr(request.app.state, "source_discovery_use_cases", None)
    if container is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The source discovery service is not available.",
        )
    return cast(SourceDiscoveryUseCases, container)


def get_analysis_use_cases(request: Request) -> AnalysisUseCases:
    container = getattr(request.app.state, "analysis_use_cases", None)
    if container is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The analysis service is not available.",
        )
    return cast(AnalysisUseCases, container)


def get_media_import_use_cases(request: Request) -> MediaImportUseCases:
    container = getattr(request.app.state, "media_import_use_cases", None)
    if container is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The media import service is not available.",
        )
    return cast(MediaImportUseCases, container)


def get_document_import_use_cases(request: Request) -> DocumentImportUseCases:
    container = getattr(request.app.state, "document_import_use_cases", None)
    if container is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The document import service is not available.",
        )
    return cast(DocumentImportUseCases, container)


def get_provider_catalog_service(request: Request) -> ProviderCatalogService:
    service = getattr(request.app.state, "provider_catalog_service", None)
    if service is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The Provider catalog service is not available.",
        )
    return cast(ProviderCatalogService, service)


def get_ai_provider_service(request: Request) -> AiProviderService:
    service = getattr(request.app.state, "ai_provider_service", None)
    if service is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The AI Provider service is not available.",
        )
    return cast(AiProviderService, service)


def get_storage_file_service(request: Request) -> StorageFileService:
    service = getattr(request.app.state, "storage_file_service", None)
    if service is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The storage file service is not available.",
        )
    return cast(StorageFileService, service)


async def get_provider_statuses(request: Request) -> tuple[ProviderStatusView, ...]:
    service = getattr(request.app.state, "provider_status_service", None)
    if service is not None:
        return await cast(ProviderStatusService, service).list()
    return cast(tuple[ProviderStatusView, ...], request.app.state.provider_statuses)
