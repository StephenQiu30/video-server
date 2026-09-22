from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import (
    get_current_admin,
    get_current_user,
    get_provider_authorization_service,
    get_provider_statuses,
)
from app.api.responses import ApiResponseRoute
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.schemas.providers import (
    BeginProviderAuthorizationRequest,
    ProviderAuthorizationResponse,
    ProviderAuthorizationStatus,
    ProviderListResponse,
)
from app.services.auth.models import CurrentUser
from app.services.provider_authorization import (
    ProviderAuthorizationError,
    ProviderAuthorizationService,
)
from app.services.providers import ProviderStatusView

router = APIRouter(
    route_class=ApiResponseRoute, prefix="/providers", tags=["providers"]
)
User = Annotated[CurrentUser, Depends(get_current_user)]
Admin = Annotated[CurrentUser, Depends(get_current_admin)]
Statuses = Annotated[tuple[ProviderStatusView, ...], Depends(get_provider_statuses)]
Authorizations = Annotated[
    ProviderAuthorizationService, Depends(get_provider_authorization_service)
]


@router.get(
    "",
    operation_id="listProviders",
    response_model=ProviderListResponse,
    summary="查询平台能力状态",
)
async def list_providers(_user: User, statuses: Statuses) -> ProviderListResponse:
    """返回不含凭据、出口地址和 Canary 目标的能力快照。"""
    return ProviderListResponse.from_views(statuses)


@router.post(
    "/{provider_key}/authorization",
    operation_id="beginProviderAuthorization",
    response_model=ProviderAuthorizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="发起本机平台授权",
)
async def begin_provider_authorization(
    provider_key: str,
    user: Admin,
    authorizations: Authorizations,
    request: BeginProviderAuthorizationRequest,
) -> ProviderAuthorizationResponse:
    """由本机 Access Agent 使用明确选择的 Chrome 来源完成平台授权。"""
    try:
        transaction = await authorizations.begin(
            user.id,
            provider_key,
            request.source,
        )
    except ProviderAuthorizationError as exc:
        _raise_authorization_error(exc)
    return ProviderAuthorizationResponse(
        transaction_id=transaction.transaction_id,
        provider_key=transaction.provider_key,
        status=ProviderAuthorizationStatus(transaction.status),
        expires_at=transaction.expires_at,
    )


@router.get(
    "/authorization/{transaction_id}",
    operation_id="getProviderAuthorization",
    response_model=ProviderAuthorizationResponse,
    summary="查询本机平台授权",
)
async def get_provider_authorization(
    transaction_id: str,
    user: User,
    authorizations: Authorizations,
) -> ProviderAuthorizationResponse:
    try:
        transaction = await authorizations.get(user.id, transaction_id)
    except ProviderAuthorizationError as exc:
        _raise_authorization_error(exc)
    return ProviderAuthorizationResponse(
        transaction_id=transaction.transaction_id,
        provider_key=transaction.provider_key,
        status=ProviderAuthorizationStatus(transaction.status),
        expires_at=transaction.expires_at,
    )


@router.delete(
    "/authorization/{transaction_id}",
    operation_id="cancelProviderAuthorization",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="取消本机平台授权",
)
async def cancel_provider_authorization(
    transaction_id: str,
    user: User,
    authorizations: Authorizations,
) -> Response:
    try:
        await authorizations.cancel(user.id, transaction_id)
    except ProviderAuthorizationError as exc:
        _raise_authorization_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _raise_authorization_error(error: ProviderAuthorizationError) -> None:
    if error.code == "provider_unsupported":
        raise AppError(
            status=422,
            code=ErrorCode.PROVIDER_UNSUPPORTED,
            title="Provider authorization unavailable",
            detail=error.detail,
        )
    if error.code == "not_found":
        raise AppError(
            status=404,
            code=ErrorCode.NOT_FOUND,
            title="Authorization not found",
            detail=error.detail,
        )
    if error.code == "provider_configuration_missing":
        raise AppError(
            status=503,
            code=ErrorCode.PROVIDER_CONFIGURATION_MISSING,
            title="Provider configuration missing",
            detail=error.detail,
        )
    raise AppError(
        status=503,
        code=ErrorCode.PROVIDER_AUTHORIZATION_UNAVAILABLE,
        title="Provider authorization unavailable",
        detail=error.detail,
    )
