from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import AwareDatetime

from app.api.deps import get_current_admin, get_services
from app.api.responses import ApiResponseRoute
from app.core.errors import AppError
from app.schemas.operation_logs import (
    OperationLogPageResponse,
    OperationLogResponse,
    OperationOutcome,
)
from app.services.auth.models import CurrentUser

router = APIRouter(
    route_class=ApiResponseRoute, prefix="/admin/operation-logs", tags=["admin"]
)


@router.get(
    "",
    operation_id="listOperationLogs",
    response_model=OperationLogPageResponse,
    summary="查询全系统操作日志",
)
async def list_operation_logs(
    request: Request,
    response: Response,
    admin: Annotated[CurrentUser, Depends(get_current_admin)],
    page: Annotated[int, Query(ge=1, le=10000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
    q: Annotated[str | None, Query(max_length=128)] = None,
    outcome: OperationOutcome | None = None,
    created_from: AwareDatetime | None = None,
    created_to: AwareDatetime | None = None,
    admin_only: bool = False,
    source: Literal["request", "task"] | None = None,
) -> OperationLogPageResponse:
    response.headers["Cache-Control"] = "no-store"
    if created_from and created_to and created_from > created_to:
        raise AppError(
            status=422,
            code="invalid_request",
            title="Invalid date range",
            detail="Start must not be after end.",
        )
    store = get_services(request).operation_log_store
    if store is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Unavailable",
            detail="Operation log store is unavailable.",
        )
    result = await store.list(
        page=page,
        page_size=page_size,
        q=q,
        outcome=outcome,
        created_from=created_from,
        created_to=created_to,
        admin_only=admin_only,
        source=source,
    )
    return OperationLogPageResponse(
        items=[
            OperationLogResponse.model_validate(row, from_attributes=True)
            for row in result.items
        ],
        page=page,
        page_size=page_size,
        total=result.total,
    )
