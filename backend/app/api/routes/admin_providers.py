from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_current_admin, get_provider_catalog_service
from app.api.responses import ApiResponseRoute
from app.schemas.provider_catalog import (
    CreateProviderCatalogEntryRequest,
    ProviderCatalogEntryResponse,
    ProviderCatalogListResponse,
    UpdateProviderCatalogEntryRequest,
)
from app.services.auth.models import CurrentUser
from app.services.provider_catalog import (
    ProviderCatalogService,
)

router = APIRouter(
    route_class=ApiResponseRoute, prefix="/admin/providers", tags=["admin"]
)
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
    items = await catalog.list_entries(admin)
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
    item = await catalog.create_entry(admin, **body.model_dump())
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
    item = await catalog.update_entry(
        admin,
        provider_key,
        **body.model_dump(),
    )
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
    await catalog.delete_entry(admin, provider_key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
