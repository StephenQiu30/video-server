from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_provider_statuses
from app.api.schemas.providers import ProviderListResponse
from app.application.auth import CurrentUser
from app.application.providers import ProviderStatusView

router = APIRouter(prefix="/providers", tags=["providers"])
User = Annotated[CurrentUser, Depends(get_current_user)]
Statuses = Annotated[tuple[ProviderStatusView, ...], Depends(get_provider_statuses)]


@router.get(
    "",
    operation_id="listProviders",
    response_model=ProviderListResponse,
    summary="查询平台能力状态",
)
async def list_providers(_user: User, statuses: Statuses) -> ProviderListResponse:
    """返回不含凭据、出口地址和 Canary 目标的能力快照。"""
    return ProviderListResponse.from_views(statuses)
