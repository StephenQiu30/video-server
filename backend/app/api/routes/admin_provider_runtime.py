from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin, get_provider_statuses
from app.schemas.provider_runtime import (
    ProviderRuntimeListResponse,
    ProviderRuntimeResponse,
)
from app.services.auth.models import CurrentUser
from app.services.providers import ProviderStatusView

router = APIRouter(prefix="/admin/provider-runtime", tags=["admin"])


@router.get(
    "",
    operation_id="getAdminProviderRuntime",
    response_model=ProviderRuntimeListResponse,
    summary="读取已开放平台的脱敏运行诊断",
)
async def get_admin_provider_runtime(
    _admin: Annotated[CurrentUser, Depends(get_current_admin)],
    statuses: Annotated[tuple[ProviderStatusView, ...], Depends(get_provider_statuses)],
) -> ProviderRuntimeListResponse:
    """仅元数据快照，不登录、不导出会话、不解析或下载媒体。"""
    return ProviderRuntimeListResponse(
        items=tuple(ProviderRuntimeResponse.from_view(item) for item in statuses)
    )
