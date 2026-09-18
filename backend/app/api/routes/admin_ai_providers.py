from __future__ import annotations

from dataclasses import asdict
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_ai_provider_service, get_current_admin
from app.api.responses import ApiResponseRoute
from app.schemas.ai_providers import (
    AiModelListResponse,
    AiModelResponse,
    AiProviderProfileListResponse,
    AiProviderProfileResponse,
    CreateAiProviderProfileRequest,
    UpdateAiProviderProfileRequest,
)
from app.services.ai_providers import (
    AiProviderService,
)
from app.services.auth.models import CurrentUser

router = APIRouter(
    route_class=ApiResponseRoute, prefix="/admin/ai-providers", tags=["admin"]
)
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
    items = await providers.list_profiles(admin)
    agent_available = await providers.agent_available(admin)
    return AiProviderProfileListResponse(
        items=tuple(AiProviderProfileResponse.from_domain(item) for item in items),
        agent_available=agent_available,
    )


@router.get(
    "/models/openrouter",
    operation_id="listOpenRouterModels",
    response_model=AiModelListResponse,
    summary="查询 OpenRouter 公开模型能力",
)
async def list_openrouter_models(
    admin: Admin, providers: Providers
) -> AiModelListResponse:
    models = await providers.list_models(admin)
    return AiModelListResponse(
        items=tuple(AiModelResponse.model_validate(asdict(model)) for model in models)
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
    item = await providers.activate_profile(admin, provider_key)
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
    await providers.delete_profile(admin, provider_key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
