from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import (
    DownloadUseCases,
    IdempotencyKey,
    get_download_use_cases,
)
from app.api.errors import application_error
from app.api.schemas.inspections import InspectionRequest, InspectionResponse
from app.application.auth import CurrentUser
from app.application.downloads import ApplicationError

router = APIRouter(prefix="/inspections", tags=["inspections"])
User = Annotated[CurrentUser, Depends(get_current_user)]
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
    user: User,
    use_cases: UseCases,
    response: Response,
) -> InspectionResponse:
    """校验公开媒体地址并返回可供选择的语义下载格式。"""
    try:
        view = await use_cases.inspect_media(body.url, user.owner_hash, idempotency_key)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    response.headers["Location"] = f"/api/inspections/{view.id}"
    return InspectionResponse.from_view(view)


@router.get(
    "/{inspection_id}/thumbnail",
    operation_id="getInspectionThumbnail",
    response_class=Response,
    responses={
        200: {
            "description": "Private persisted media thumbnail",
            "content": {
                "image/avif": {},
                "image/jpeg": {},
                "image/png": {},
                "image/webp": {},
            },
        }
    },
    summary="读取持久化媒体封面",
)
async def get_inspection_thumbnail(
    inspection_id: UUID,
    user: User,
    use_cases: UseCases,
) -> Response:
    """读取当前用户拥有且存储在私有对象存储中的媒体封面。"""
    try:
        thumbnail = await use_cases.get_thumbnail(inspection_id, user.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return Response(
        content=thumbnail.content,
        media_type=thumbnail.content_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "ETag": f'"{thumbnail.sha256}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{inspection_id}",
    operation_id="getInspection",
    response_model=InspectionResponse,
    summary="查询媒体解析结果",
)
async def get_inspection(
    inspection_id: UUID,
    user: User,
    use_cases: UseCases,
) -> InspectionResponse:
    """查询当前登录用户拥有的媒体解析结果。"""
    try:
        view = await use_cases.get_inspection(inspection_id, user.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return InspectionResponse.from_view(view)
