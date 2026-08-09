from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import (
    AnalysisUseCases,
    IdempotencyKey,
    get_analysis_use_cases,
)
from app.api.errors import analysis_application_error
from app.api.schemas.analyses import AnalysisRequest, AnalysisResponse
from app.application.analysis import AnalysisApplicationError
from app.application.auth import CurrentUser

router = APIRouter(tags=["analyses"])
User = Annotated[CurrentUser, Depends(get_current_user)]
UseCases = Annotated[AnalysisUseCases, Depends(get_analysis_use_cases)]


@router.post(
    "/downloads/{download_id}/analyses",
    operation_id="createAnalysis",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建视频分析任务",
)
async def create_analysis(
    download_id: UUID,
    body: AnalysisRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    user: User,
    use_cases: UseCases,
) -> AnalysisResponse:
    """基于已完成的下载制品创建异步 AI 分析任务。"""
    try:
        view = await use_cases.create_analysis(
            download_id,
            user.owner_hash,
            idempotency_key,
            body.profile,
            body.output_language,
        )
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    response.headers["Location"] = f"/api/analyses/{view.id}"
    return AnalysisResponse.from_view(view)


@router.get(
    "/analyses/{analysis_id}",
    operation_id="getAnalysis",
    response_model=AnalysisResponse,
    summary="查询视频分析任务",
)
async def get_analysis(
    analysis_id: UUID,
    user: User,
    use_cases: UseCases,
) -> AnalysisResponse:
    """查询分析进度及经过证据校验的结果。"""
    try:
        view = await use_cases.get_analysis(analysis_id, user.owner_hash)
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    return AnalysisResponse.from_view(view)


@router.post(
    "/analyses/{analysis_id}/cancel",
    operation_id="cancelAnalysis",
    response_model=AnalysisResponse,
    summary="取消视频分析任务",
)
async def cancel_analysis(
    analysis_id: UUID,
    user: User,
    use_cases: UseCases,
) -> AnalysisResponse:
    """请求取消尚未结束的视频分析任务。"""
    try:
        view = await use_cases.cancel_analysis(analysis_id, user.owner_hash)
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    return AnalysisResponse.from_view(view)
