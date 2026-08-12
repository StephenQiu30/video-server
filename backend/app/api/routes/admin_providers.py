from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response, status

from app.api.auth_dependencies import get_current_admin
from app.api.dependencies import get_provider_catalog_service
from app.api.schemas.provider_catalog import (
    CreateProviderCatalogEntryRequest,
    ProviderCatalogEntryResponse,
    ProviderCatalogListResponse,
    UpdateProviderCatalogEntryRequest,
)
from app.application.auth import CurrentUser
from app.application.provider_catalog import (
    ProviderCatalogError,
    ProviderCatalogErrorCode,
    ProviderCatalogService,
)
from app.core.errors import AppError

router = APIRouter(prefix="/admin/providers", tags=["admin"])
Admin = Annotated[CurrentUser, Depends(get_current_admin)]
Catalog = Annotated[ProviderCatalogService, Depends(get_provider_catalog_service)]


@router.get(
    "",
    operation_id="listProviderCatalogEntries",
    response_model=ProviderCatalogListResponse,
    summary="查询平台目录",
)
async def list_provider_catalog_entries(
    admin: Admin, catalog: Catalog
) -> ProviderCatalogListResponse:
    try:
        items = await catalog.list_entries(admin)
    except ProviderCatalogError as exc:
        raise _catalog_error(exc) from exc
    return ProviderCatalogListResponse(
        items=tuple(ProviderCatalogEntryResponse.from_view(item) for item in items)
    )


@router.post(
    "",
    operation_id="createProviderCatalogEntry",
    response_model=ProviderCatalogEntryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "headers": {
                "Location": {
                    "description": "新建平台目录条目的资源地址。",
                    "schema": {"type": "string"},
                }
            }
        }
    },
    summary="新增平台目录条目",
)
async def create_provider_catalog_entry(
    body: CreateProviderCatalogEntryRequest,
    admin: Admin,
    catalog: Catalog,
    response: Response,
) -> ProviderCatalogEntryResponse:
    try:
        item = await catalog.create_entry(admin, **body.model_dump())
    except ProviderCatalogError as exc:
        raise _catalog_error(exc) from exc
    response.headers["Location"] = f"/api/admin/providers/{quote(item.entry.key)}"
    return ProviderCatalogEntryResponse.from_view(item)


@router.patch(
    "/{provider_key}",
    operation_id="updateProviderCatalogEntry",
    response_model=ProviderCatalogEntryResponse,
    summary="更新平台目录条目",
)
async def update_provider_catalog_entry(
    provider_key: str,
    body: UpdateProviderCatalogEntryRequest,
    admin: Admin,
    catalog: Catalog,
) -> ProviderCatalogEntryResponse:
    try:
        item = await catalog.update_entry(
            admin,
            provider_key,
            **body.model_dump(),
        )
    except ProviderCatalogError as exc:
        raise _catalog_error(exc) from exc
    return ProviderCatalogEntryResponse.from_view(item)


@router.delete(
    "/{provider_key}",
    operation_id="deleteProviderCatalogEntry",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除平台目录条目",
)
async def delete_provider_catalog_entry(
    provider_key: str,
    admin: Admin,
    catalog: Catalog,
) -> Response:
    try:
        await catalog.delete_entry(admin, provider_key)
    except ProviderCatalogError as exc:
        raise _catalog_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _catalog_error(error: ProviderCatalogError) -> AppError:
    mapping = {
        ProviderCatalogErrorCode.FORBIDDEN: (
            403,
            "Forbidden",
            "Administrator access is required.",
        ),
        ProviderCatalogErrorCode.INVALID_ENTRY: (
            422,
            "Invalid Provider catalog entry",
            "The Provider catalog entry is invalid.",
        ),
        ProviderCatalogErrorCode.CONFLICT: (
            409,
            "Provider catalog conflict",
            "A Provider catalog entry with this key already exists.",
        ),
        ProviderCatalogErrorCode.NOT_FOUND: (
            404,
            "Provider catalog entry not found",
            "The requested Provider catalog entry does not exist.",
        ),
    }
    status_code, title, detail = mapping[error.code]
    return AppError(
        status=status_code,
        code=error.code.value,
        title=title,
        detail=detail,
    )
