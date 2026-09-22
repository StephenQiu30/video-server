from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.api.admission import RateLimitAdmission
from app.api.deps import IdempotencyKey, get_current_user, get_services, require_service
from app.api.responses import ApiResponseRoute
from app.schemas.download_intents import IntentRequest, IntentResponse
from app.services.auth.models import CurrentUser
from app.services.downloads.intents import IntentService

router = APIRouter(
    route_class=ApiResponseRoute, prefix="/download-intents", tags=["download-intents"]
)


def get_intent_service(request: Request) -> IntentService:
    return require_service(get_services(request).intent_service, "parse intent")


User = Annotated[CurrentUser, Depends(get_current_user)]
Service = Annotated[IntentService, Depends(get_intent_service)]


@router.post(
    "",
    status_code=202,
    response_model=IntentResponse,
    operation_id="createDownloadIntent",
    dependencies=[Depends(RateLimitAdmission("inspect"))],
    summary="提交持久解析意图",
)
async def create_intent(
    body: IntentRequest,
    idempotency_key: IdempotencyKey,
    user: User,
    service: Service,
    response: Response,
) -> IntentResponse:
    result = await service.create(
        body.input, user.owner_hash, idempotency_key, quota=user.admission_quota
    )
    response.headers["Location"] = f"/api/download-intents/{result.id}"
    response.headers["Cache-Control"] = "no-store"
    return IntentResponse.from_snapshot(result)


@router.get(
    "/{intent_id}",
    response_model=IntentResponse,
    operation_id="getDownloadIntent",
    summary="查询当前用户的解析意图",
)
async def get_intent(
    intent_id: UUID, user: User, service: Service, response: Response
) -> IntentResponse:
    response.headers["Cache-Control"] = "no-store"
    return IntentResponse.from_snapshot(await service.get(intent_id, user.owner_hash))


@router.post(
    "/{intent_id}/cancel",
    response_model=IntentResponse,
    operation_id="cancelDownloadIntent",
    summary="取消当前用户的解析意图",
)
async def cancel_intent(
    intent_id: UUID, user: User, service: Service, response: Response
) -> IntentResponse:
    response.headers["Cache-Control"] = "no-store"
    return IntentResponse.from_snapshot(
        await service.cancel(intent_id, user.owner_hash)
    )
