from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_current_admin, get_storage_file_service
from app.api.responses import ApiResponseRoute
from app.schemas.admin_files import (
    StorageCleanupRequest,
    StorageCleanupResponse,
    StoredFileListResponse,
)
from app.services.auth.models import CurrentUser
from app.services.storage_files.models import StoredFileCategory
from app.services.storage_files.service import StorageFileService

router = APIRouter(route_class=ApiResponseRoute, prefix="/admin/files", tags=["admin"])
Admin = Annotated[CurrentUser, Depends(get_current_admin)]
StorageFiles = Annotated[StorageFileService, Depends(get_storage_file_service)]


@router.get(
    "",
    operation_id="listStoredFiles",
    response_model=StoredFileListResponse,
    summary="分页查询持久文件",
)
async def list_stored_files(
    admin: Admin,
    service: StorageFiles,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> StoredFileListResponse:
    result = await service.list_files(page=page, page_size=page_size)
    return StoredFileListResponse.from_page(result)


@router.delete(
    "/{category}/{file_id}",
    operation_id="deleteStoredFile",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除指定持久文件",
)
async def delete_stored_file(
    category: StoredFileCategory,
    file_id: UUID,
    admin: Admin,
    service: StorageFiles,
) -> Response:
    await service.delete_file(category=category, file_id=file_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/cleanup",
    operation_id="cleanupStoredFiles",
    response_model=StorageCleanupResponse,
    summary="手动清理指定天数前的文件",
)
async def cleanup_stored_files(
    body: StorageCleanupRequest,
    admin: Admin,
    service: StorageFiles,
) -> StorageCleanupResponse:
    result = await service.cleanup(older_than_days=body.older_than_days)
    return StorageCleanupResponse.from_result(result)
