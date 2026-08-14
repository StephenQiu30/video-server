from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import RequestValidationError

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import (
    AnalysisUseCases,
    IdempotencyKey,
    get_analysis_use_cases,
)
from app.api.errors import analysis_application_error
from app.api.schemas.analyses import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisSkillResponse,
)
from app.application.analysis import (
    DOCX_MEDIA_TYPE,
    MARKDOWN_MEDIA_TYPE,
    AnalysisApplicationError,
)
from app.application.auth import CurrentUser
from app.domain.analysis import AnalysisInputKind

router = APIRouter(tags=["analyses"])
User = Annotated[CurrentUser, Depends(get_current_user)]
UseCases = Annotated[AnalysisUseCases, Depends(get_analysis_use_cases)]


@router.get(
    "/analysis-skills",
    operation_id="listAnalysisSkills",
    response_model=tuple[AnalysisSkillResponse, ...],
    summary="列出输入兼容的分析 Skill",
)
async def list_analysis_skills(
    use_cases: UseCases,
    input_kind: AnalysisInputKind,
) -> tuple[AnalysisSkillResponse, ...]:
    """按输入类型返回可选 Skill 及用户可编辑的默认提示词。"""
    return tuple(
        AnalysisSkillResponse.model_validate(skill)
        for skill in use_cases.list_analysis_skills(input_kind)
    )


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
            body.skill_id,
            body.output_language,
            body.custom_prompt,
        )
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    response.headers["Location"] = f"/api/analyses/{view.id}"
    return AnalysisResponse.from_view(view)


@router.get(
    "/downloads/{download_id}/analysis",
    operation_id="getLatestDownloadAnalysis",
    response_model=AnalysisResponse | None,
    summary="读取下载任务最近的视频分析",
)
async def get_latest_download_analysis(
    download_id: UUID,
    user: User,
    use_cases: UseCases,
) -> AnalysisResponse | None:
    """恢复当前用户在该下载任务上最近创建的分析与报告。"""
    try:
        view = await use_cases.get_latest_download_analysis(
            download_id, user.owner_hash
        )
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    return None if view is None else AnalysisResponse.from_view(view)


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


@router.get(
    "/analyses/{analysis_id}/report.md",
    operation_id="exportAnalysisMarkdown",
    response_class=Response,
    responses={
        200: {
            "description": "Canonical Markdown analysis report",
            "content": {
                "text/markdown": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
    summary="导出 Markdown 视频分析报告",
)
async def export_analysis_markdown(
    analysis_id: UUID,
    user: User,
    use_cases: UseCases,
) -> Response:
    """导出与前端预览、DOCX 转换共用的唯一 Markdown 报告。"""
    try:
        report = await use_cases.export_analysis_markdown(analysis_id, user.owner_hash)
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    return Response(
        content=report.content,
        media_type=MARKDOWN_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{report.filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/analyses/{analysis_id}/report.docx",
    operation_id="exportAnalysisReport",
    response_class=Response,
    responses={
        200: {
            "description": "Microsoft Word analysis report",
            "content": {
                DOCX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
    summary="导出视频分析报告",
)
async def export_analysis_report(
    analysis_id: UUID,
    user: User,
    use_cases: UseCases,
) -> Response:
    """将已完成的结构化分析结果导出为 DOCX 报告。"""
    try:
        report = await use_cases.export_analysis_report(analysis_id, user.owner_hash)
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    return Response(
        content=report.content,
        media_type=report.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{report.filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


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


@router.post(
    "/analyses/{analysis_id}/retry",
    operation_id="retryAnalysis",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="重试原视频分析任务",
)
async def retry_analysis(
    analysis_id: UUID,
    request: Request,
    idempotency_key: IdempotencyKey,
    response: Response,
    user: User,
    use_cases: UseCases,
) -> AnalysisResponse:
    """为同一分析任务创建下一执行代次，不改变任务资源 ID。

    Retry 是上一运行的无参数重放；带请求体的请求按校验错误拒绝。
    """
    if (await request.body()).strip() not in {b"", b"null"}:
        raise RequestValidationError(
            errors=[
                {
                    "type": "extra_forbidden",
                    "loc": ("body",),
                    "msg": "Retry does not accept a request body.",
                    "input": None,
                }
            ]
        )
    try:
        view = await use_cases.retry_analysis(
            analysis_id, user.owner_hash, idempotency_key
        )
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    response.headers["Location"] = f"/api/analyses/{view.id}"
    return AnalysisResponse.from_view(view)


@router.delete(
    "/analyses/{analysis_id}",
    operation_id="deleteAnalysis",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除视频分析与报告",
)
async def delete_analysis(
    analysis_id: UUID,
    user: User,
    use_cases: UseCases,
) -> Response:
    """隐藏分析任务并异步清理其私有报告对象。"""
    try:
        await use_cases.delete_analysis(analysis_id, user.owner_hash)
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
