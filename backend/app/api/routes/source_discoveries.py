from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.admission import RateLimitAdmission
from app.api.deps import (
    IdempotencyKey,
    get_current_user,
    get_source_discovery_use_cases,
)
from app.api.responses import ApiResponseRoute
from app.core.runtime import SourceDiscoveryUseCases
from app.schemas.source_discoveries import (
    SourceDiscoveryRequest,
    SourceDiscoveryResponse,
)
from app.services.auth.models import CurrentUser

router = APIRouter(
    route_class=ApiResponseRoute,
    prefix="/source-discoveries",
    tags=["source-discoveries"],
)
User = Annotated[CurrentUser, Depends(get_current_user)]
UseCases = Annotated[SourceDiscoveryUseCases, Depends(get_source_discovery_use_cases)]


@router.post(
    "",
    operation_id="createSourceDiscovery",
    dependencies=[Depends(RateLimitAdmission("inspect"))],
    response_model=SourceDiscoveryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="发现微信公众号文章中的视频",
)
async def create_source_discovery(
    body: SourceDiscoveryRequest,
    idempotency_key: IdempotencyKey,
    user: User,
    use_cases: UseCases,
    response: Response,
) -> SourceDiscoveryResponse:
    view = await use_cases.create(body.url, user.owner_hash, idempotency_key)
    response.headers["Location"] = f"/api/source-discoveries/{view.id}"
    return SourceDiscoveryResponse.from_view(view)


@router.get(
    "/{discovery_id}",
    operation_id="getSourceDiscovery",
    response_model=SourceDiscoveryResponse,
    summary="查询文章视频发现结果",
)
async def get_source_discovery(
    discovery_id: UUID,
    user: User,
    use_cases: UseCases,
) -> SourceDiscoveryResponse:
    view = await use_cases.get(discovery_id, user.owner_hash)
    return SourceDiscoveryResponse.from_view(view)
