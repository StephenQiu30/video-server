"""Owner-scoped browser upload endpoints for screenplay documents."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import (
    DocumentImportUseCases,
    IdempotencyKey,
    get_document_import_use_cases,
)
from app.api.errors import import_application_error
from app.api.schemas.documents import (
    CompleteDocumentImportRequest,
    DocumentImportRequest,
    DocumentImportResponse,
    DocumentPageResponse,
    DocumentResponse,
    DocumentUploadSessionResponse,
)
from app.application.auth import CurrentUser
from app.application.imports import CompletedUploadPart, ImportApplicationError
from app.domain.imports import ContentKind, ImportSourceFormat

router = APIRouter(prefix="/documents", tags=["documents"])
User = Annotated[CurrentUser, Depends(get_current_user)]
UseCases = Annotated[DocumentImportUseCases, Depends(get_document_import_use_cases)]


@router.post(
    "",
    operation_id="createDocumentImport",
    response_model=DocumentImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建剧本文档导入",
)
async def create_document_import(
    body: DocumentImportRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    user: User,
    use_cases: UseCases,
) -> DocumentImportResponse:
    try:
        view = await use_cases.create_resource(
            owner_hash=user.owner_hash,
            idempotency_key=idempotency_key,
            content_kind=ContentKind.SCREENPLAY,
            source_format=ImportSourceFormat(body.source_format),
            file_name=body.file_name,
            declared_size_bytes=body.declared_size_bytes,
            declared_sha256=body.declared_sha256,
            rights_accepted=body.rights_accepted,
        )
    except ImportApplicationError as error:
        raise import_application_error(error) from error
    response.headers["Location"] = f"/api/documents/{view.id}"
    response.headers["Cache-Control"] = "no-store"
    return DocumentImportResponse.from_view(view)


@router.get(
    "",
    operation_id="listDocuments",
    response_model=DocumentPageResponse,
    summary="查询剧本文档列表",
)
async def list_documents(
    user: User,
    use_cases: UseCases,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> DocumentPageResponse:
    try:
        view = await use_cases.list_documents(
            user.owner_hash, page=page, page_size=page_size
        )
    except ImportApplicationError as error:
        raise import_application_error(error) from error
    return DocumentPageResponse.from_view(view)


@router.get(
    "/{document_id}",
    operation_id="getDocumentImport",
    response_model=DocumentResponse,
    summary="查询剧本文档导入",
)
async def get_document_import(
    document_id: UUID,
    response: Response,
    user: User,
    use_cases: UseCases,
) -> DocumentResponse:
    try:
        view = await use_cases.get_document(document_id, user.owner_hash)
    except ImportApplicationError as error:
        raise import_application_error(error) from error
    response.headers["Cache-Control"] = "no-store"
    return DocumentResponse.from_view(view)


@router.delete(
    "/{document_id}",
    operation_id="deleteDocument",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除剧本文档及其制品",
)
async def delete_document(
    document_id: UUID,
    user: User,
    use_cases: UseCases,
) -> Response:
    try:
        await use_cases.delete_document(document_id, user.owner_hash)
    except ImportApplicationError as error:
        raise import_application_error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{document_id}/upload-sessions",
    operation_id="createDocumentUploadSession",
    response_model=DocumentUploadSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建或刷新文档上传会话",
)
async def create_document_upload_session(
    document_id: UUID,
    response: Response,
    user: User,
    use_cases: UseCases,
) -> DocumentUploadSessionResponse:
    try:
        view = await use_cases.create_upload_session(
            document_id, user.owner_hash, ContentKind.SCREENPLAY
        )
    except ImportApplicationError as error:
        raise import_application_error(error) from error
    response.headers["Cache-Control"] = "no-store"
    return DocumentUploadSessionResponse.from_view(view)


@router.post(
    "/{document_id}/complete",
    operation_id="completeDocumentImport",
    response_model=DocumentImportResponse,
    summary="完成文档上传并触发验证",
)
async def complete_document_import(
    document_id: UUID,
    body: CompleteDocumentImportRequest,
    response: Response,
    user: User,
    use_cases: UseCases,
) -> DocumentImportResponse:
    try:
        view = await use_cases.complete_upload(
            document_id,
            user.owner_hash,
            ContentKind.SCREENPLAY,
            tuple(
                CompletedUploadPart(part.part_number, part.etag) for part in body.parts
            ),
        )
    except ImportApplicationError as error:
        raise import_application_error(error) from error
    response.headers["Cache-Control"] = "no-store"
    return DocumentImportResponse.from_view(view)


@router.post(
    "/{document_id}/cancel",
    operation_id="cancelDocumentImport",
    response_model=DocumentImportResponse,
    summary="取消剧本文档导入",
)
async def cancel_document_import(
    document_id: UUID,
    user: User,
    use_cases: UseCases,
) -> DocumentImportResponse:
    try:
        view = await use_cases.cancel_import(
            document_id, user.owner_hash, ContentKind.SCREENPLAY
        )
    except ImportApplicationError as error:
        raise import_application_error(error) from error
    return DocumentImportResponse.from_view(view)
