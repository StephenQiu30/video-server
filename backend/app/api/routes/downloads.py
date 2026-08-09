from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import (
    DownloadUseCases,
    IdempotencyKey,
    get_download_use_cases,
)
from app.api.errors import application_error
from app.api.schemas.downloads import (
    DownloadRequest,
    DownloadResponse,
    DownloadUrlResponse,
)
from app.api.schemas.history import DownloadHistoryResponse
from app.application.auth import CurrentUser
from app.application.downloads import ApplicationError
from app.domain.downloads import DownloadStatus

router = APIRouter(prefix="/downloads", tags=["downloads"])
User = Annotated[CurrentUser, Depends(get_current_user)]
UseCases = Annotated[DownloadUseCases, Depends(get_download_use_cases)]


@router.post(
    "",
    operation_id="createDownload",
    response_model=DownloadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建下载任务",
)
async def create_download(
    body: DownloadRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    user: User,
    use_cases: UseCases,
) -> DownloadResponse:
    """根据解析结果和语义格式创建异步下载任务。"""
    try:
        view = await use_cases.create_download(
            body.inspection_id,
            body.format_id,
            user.owner_hash,
            idempotency_key,
        )
    except ApplicationError as exc:
        raise application_error(exc) from exc
    response.headers["Location"] = f"/api/downloads/{view.id}"
    return DownloadResponse.from_view(view)


@router.get(
    "/history",
    operation_id="getDownloadHistory",
    response_model=DownloadHistoryResponse,
    summary="查询下载历史",
)
async def get_download_history(
    user: User,
    use_cases: UseCases,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    status_filter: Annotated[DownloadStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=128)] = None,
) -> DownloadHistoryResponse:
    """查询当前登录用户的下载历史。"""
    try:
        view = await use_cases.get_download_history(
            user.owner_hash,
            page=page,
            page_size=page_size,
            status=status_filter,
            search=search,
        )
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadHistoryResponse.from_view(view)


@router.get(
    "/{job_id}",
    operation_id="getDownload",
    response_model=DownloadResponse,
    summary="查询下载任务",
)
async def get_download(
    job_id: UUID,
    user: User,
    use_cases: UseCases,
) -> DownloadResponse:
    """查询当前登录用户拥有的下载任务。"""
    try:
        view = await use_cases.get_download(job_id, user.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadResponse.from_view(view)


@router.post(
    "/{job_id}/cancel",
    operation_id="cancelDownload",
    response_model=DownloadResponse,
    summary="取消下载任务",
)
async def cancel_download(
    job_id: UUID,
    user: User,
    use_cases: UseCases,
) -> DownloadResponse:
    """请求取消尚未结束的下载任务。"""
    try:
        view = await use_cases.cancel_download(job_id, user.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadResponse.from_view(view)


@router.post(
    "/{job_id}/download-url",
    operation_id="issueDownloadUrl",
    response_model=DownloadUrlResponse,
    summary="签发文件下载地址",
)
async def issue_download_url(
    job_id: UUID,
    user: User,
    use_cases: UseCases,
) -> DownloadUrlResponse:
    """为已完成的下载任务签发短时制品地址。"""
    try:
        view = await use_cases.issue_download_url(job_id, user.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadUrlResponse.from_view(view)
