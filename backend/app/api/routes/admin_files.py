from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.auth_dependencies import get_current_admin
from app.api.dependencies import get_storage_file_service
from app.api.schemas.admin_files import (
    StorageCleanupRequest,
    StorageCleanupResponse,
    StoredFileListResponse,
)
from app.application.auth import CurrentUser
from app.application.storage_files import StorageFileService

router = APIRouter(prefix="/admin/files", tags=["admin"])
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
