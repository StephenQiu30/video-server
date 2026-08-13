from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response, status

from app.api.auth_dependencies import get_current_admin
from app.api.dependencies import get_ai_provider_service
from app.api.schemas.ai_providers import (
    AiProviderProfileListResponse,
    AiProviderProfileResponse,
    CreateAiProviderProfileRequest,
    UpdateAiProviderProfileRequest,
)
from app.application.ai_providers import (
    AiProviderError,
    AiProviderErrorCode,
    AiProviderService,
)
from app.application.auth import CurrentUser
from app.core.errors import AppError

router = APIRouter(prefix="/admin/ai-providers", tags=["admin"])
Admin = Annotated[CurrentUser, Depends(get_current_admin)]
Providers = Annotated[AiProviderService, Depends(get_ai_provider_service)]


@router.get(
    "",
    operation_id="listAiProviderProfiles",
    response_model=AiProviderProfileListResponse,
    summary="查询 AI 分析 Provider",
)
async def list_ai_provider_profiles(
    admin: Admin, providers: Providers
) -> AiProviderProfileListResponse:
    try:
        items = await providers.list_profiles(admin)
        agent_available = await providers.agent_available(admin)
    except AiProviderError as exc:
        raise _provider_error(exc) from exc
    return AiProviderProfileListResponse(
        items=tuple(AiProviderProfileResponse.from_domain(item) for item in items),
        agent_available=agent_available,
    )


@router.post(
    "",
    operation_id="createAiProviderProfile",
    response_model=AiProviderProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增 AI 分析 Provider",
)
async def create_ai_provider_profile(
    body: CreateAiProviderProfileRequest,
    admin: Admin,
    providers: Providers,
    response: Response,
) -> AiProviderProfileResponse:
    try:
        item = await providers.create_profile(
            admin,
            key=body.key,
            display_name=body.display_name,
            engine=body.engine,
            auth_mode=body.auth_mode,
            base_url=body.base_url,
            model=body.model,
            api_key=body.api_key.get_secret_value() if body.api_key else None,
        )
    except AiProviderError as exc:
        raise _provider_error(exc) from exc
    response.headers["Location"] = f"/api/admin/ai-providers/{quote(item.key)}"
    return AiProviderProfileResponse.from_domain(item)


@router.patch(
    "/{provider_key}",
    operation_id="updateAiProviderProfile",
    response_model=AiProviderProfileResponse,
    summary="更新 AI 分析 Provider",
)
async def update_ai_provider_profile(
    provider_key: str,
    body: UpdateAiProviderProfileRequest,
    admin: Admin,
    providers: Providers,
) -> AiProviderProfileResponse:
    try:
        item = await providers.update_profile(
            admin,
            provider_key,
            display_name=body.display_name,
            engine=body.engine,
            auth_mode=body.auth_mode,
            base_url=body.base_url,
            base_url_changed="base_url" in body.model_fields_set,
            model=body.model,
            api_key=body.api_key.get_secret_value() if body.api_key else None,
        )
    except AiProviderError as exc:
        raise _provider_error(exc) from exc
    return AiProviderProfileResponse.from_domain(item)


@router.post(
    "/{provider_key}/activate",
    operation_id="activateAiProviderProfile",
    response_model=AiProviderProfileResponse,
    summary="启用 AI 分析 Provider",
)
async def activate_ai_provider_profile(
    provider_key: str,
    admin: Admin,
    providers: Providers,
) -> AiProviderProfileResponse:
    try:
        item = await providers.activate_profile(admin, provider_key)
    except AiProviderError as exc:
        raise _provider_error(exc) from exc
    return AiProviderProfileResponse.from_domain(item)


@router.delete(
    "/{provider_key}",
    operation_id="deleteAiProviderProfile",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除 AI 分析 Provider",
)
async def delete_ai_provider_profile(
    provider_key: str,
    admin: Admin,
    providers: Providers,
) -> Response:
    try:
        await providers.delete_profile(admin, provider_key)
    except AiProviderError as exc:
        raise _provider_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _provider_error(error: AiProviderError) -> AppError:
    mapping = {
        AiProviderErrorCode.FORBIDDEN: (
            403,
            "Forbidden",
            "Administrator access is required.",
        ),
        AiProviderErrorCode.INVALID_PROFILE: (
            422,
            "Invalid AI Provider profile",
            "The AI Provider profile is invalid or incomplete.",
        ),
        AiProviderErrorCode.CONFLICT: (
            409,
            "AI Provider conflict",
            "An AI Provider profile with this key already exists.",
        ),
        AiProviderErrorCode.NOT_FOUND: (
            404,
            "AI Provider not found",
            "The requested AI Provider profile does not exist.",
        ),
        AiProviderErrorCode.ACTIVE_DELETE: (
            409,
            "Active AI Provider cannot be deleted",
            "Activate another AI Provider before deleting this profile.",
        ),
    }
    status_code, title, detail = mapping[error.code]
    return AppError(
        status=status_code,
        code=error.code.value,
        title=title,
        detail=detail,
    )
