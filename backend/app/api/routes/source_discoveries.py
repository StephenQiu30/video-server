from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.admission import RateLimitAdmission
from app.api.auth_dependencies import get_current_user
from app.api.dependencies import (
    IdempotencyKey,
    SourceDiscoveryUseCases,
    get_source_discovery_use_cases,
)
from app.api.errors import application_error
from app.api.schemas.source_discoveries import (
    SourceDiscoveryRequest,
    SourceDiscoveryResponse,
)
from app.application.auth import CurrentUser
from app.application.downloads import ApplicationError

router = APIRouter(prefix="/source-discoveries", tags=["source-discoveries"])
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
    try:
        view = await use_cases.create(body.url, user.owner_hash, idempotency_key)
    except ApplicationError as exc:
        raise application_error(exc) from exc
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
    try:
        view = await use_cases.get(discovery_id, user.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return SourceDiscoveryResponse.from_view(view)
