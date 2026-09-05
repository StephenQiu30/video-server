from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.admission import RateLimitAdmission
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
    "/documents/{document_id}/analyses",
    operation_id="createDocumentAnalysis",
    dependencies=[Depends(RateLimitAdmission("analysis"))],
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建剧本分析或改写任务",
)
async def create_document_analysis(
    document_id: UUID,
    body: AnalysisRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    user: User,
    use_cases: UseCases,
) -> AnalysisResponse:
    """基于已规范化的剧本文档创建异步分析或改写任务。"""
    try:
        view = await use_cases.create_document_analysis(
            document_id,
            user.owner_hash,
            idempotency_key,
            body.skill_id,
            body.output_language,
            body.custom_prompt,
        )
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    response.headers["Location"] = f"/api/analyses/{view.id}"
    return AnalysisResponse.from_view(view)


@router.get(
    "/documents/{document_id}/analysis",
    operation_id="getLatestDocumentAnalysis",
    response_model=AnalysisResponse | None,
    summary="读取文档最近的剧本分析",
)
async def get_latest_document_analysis(
    document_id: UUID,
    user: User,
    use_cases: UseCases,
) -> AnalysisResponse | None:
    """恢复当前用户在该剧本文档上最近创建的分析与报告。"""
    try:
        view = await use_cases.get_latest_document_analysis(
            document_id, user.owner_hash
        )
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    return None if view is None else AnalysisResponse.from_view(view)
