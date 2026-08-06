from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    DownloadUseCases,
    IdempotencyKey,
    get_anonymous_session,
    get_download_use_cases,
)
from app.api.errors import application_error
from app.api.schemas.inspections import InspectionRequest, InspectionResponse
from app.application.downloads import ApplicationError
from app.core.session import AnonymousSession

router = APIRouter(prefix="/inspections", tags=["inspections"])
Session = Annotated[AnonymousSession, Depends(get_anonymous_session)]
UseCases = Annotated[DownloadUseCases, Depends(get_download_use_cases)]


@router.post(
    "",
    operation_id="inspectMedia",
    response_model=InspectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="解析媒体信息",
)
async def inspect_media(
    body: InspectionRequest,
    idempotency_key: IdempotencyKey,
    session: Session,
    use_cases: UseCases,
) -> InspectionResponse:
    """校验公开媒体地址并返回可供选择的语义下载格式。"""
    try:
        view = await use_cases.inspect_media(
            body.url, session.owner_hash, idempotency_key
        )
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return InspectionResponse.from_view(view)


@router.get(
    "/{inspection_id}",
    operation_id="getInspection",
    response_model=InspectionResponse,
    summary="查询媒体解析结果",
)
async def get_inspection(
    inspection_id: UUID,
    session: Session,
    use_cases: UseCases,
) -> InspectionResponse:
    """查询当前匿名会话拥有的媒体解析结果。"""
    try:
        view = await use_cases.get_inspection(inspection_id, session.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return InspectionResponse.from_view(view)
