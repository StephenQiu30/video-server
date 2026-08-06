from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import (
    DownloadUseCases,
    IdempotencyKey,
    get_anonymous_session,
    get_download_use_cases,
)
from app.api.errors import application_error
from app.api.schemas.downloads import (
    DownloadRequest,
    DownloadResponse,
    DownloadUrlResponse,
)
from app.application.downloads import ApplicationError
from app.core.session import AnonymousSession

router = APIRouter(prefix="/downloads", tags=["downloads"])
Session = Annotated[AnonymousSession, Depends(get_anonymous_session)]
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
    session: Session,
    use_cases: UseCases,
) -> DownloadResponse:
    """根据解析结果和语义格式创建异步下载任务。"""
    try:
        view = await use_cases.create_download(
            body.inspection_id,
            body.format_id,
            session.owner_hash,
            idempotency_key,
        )
    except ApplicationError as exc:
        raise application_error(exc) from exc
    response.headers["Location"] = f"/api/downloads/{view.id}"
    return DownloadResponse.from_view(view)


@router.get(
    "/{job_id}",
    operation_id="getDownload",
    response_model=DownloadResponse,
    summary="查询下载任务",
)
async def get_download(
    job_id: UUID,
    session: Session,
    use_cases: UseCases,
) -> DownloadResponse:
    """查询当前匿名会话拥有的下载任务。"""
    try:
        view = await use_cases.get_download(job_id, session.owner_hash)
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
    session: Session,
    use_cases: UseCases,
) -> DownloadResponse:
    """请求取消尚未结束的下载任务。"""
    try:
        view = await use_cases.cancel_download(job_id, session.owner_hash)
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
    session: Session,
    use_cases: UseCases,
) -> DownloadUrlResponse:
    """为已完成的下载任务签发短时制品地址。"""
    try:
        view = await use_cases.issue_download_url(job_id, session.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadUrlResponse.from_view(view)
