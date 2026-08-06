from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.api.dependencies import (
    AnalysisUseCases,
    get_analysis_use_cases,
    get_anonymous_session,
)
from app.api.errors import analysis_application_error
from app.api.schemas import AnalysisRequest, AnalysisResponse
from app.application.analysis import AnalysisApplicationError
from app.core.session import AnonymousSession

router = APIRouter(tags=["analyses"])
Session = Annotated[AnonymousSession, Depends(get_anonymous_session)]
UseCases = Annotated[AnalysisUseCases, Depends(get_analysis_use_cases)]
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128),
]


@router.post(
    "/api/v1/downloads/{download_id}/analyses",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_analysis(
    download_id: UUID,
    body: AnalysisRequest,
    idempotency_key: IdempotencyKey,
    session: Session,
    use_cases: UseCases,
) -> AnalysisResponse:
    try:
        view = await use_cases.create_analysis(
            download_id,
            session.owner_hash,
            idempotency_key,
            body.profile,
            body.output_language,
        )
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    return AnalysisResponse.from_view(view)


@router.get(
    "/api/v1/analyses/{analysis_id}",
    response_model=AnalysisResponse,
)
async def get_analysis(
    analysis_id: UUID,
    session: Session,
    use_cases: UseCases,
) -> AnalysisResponse:
    try:
        view = await use_cases.get_analysis(analysis_id, session.owner_hash)
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    return AnalysisResponse.from_view(view)


@router.post(
    "/api/v1/analyses/{analysis_id}/cancel",
    response_model=AnalysisResponse,
)
async def cancel_analysis(
    analysis_id: UUID,
    session: Session,
    use_cases: UseCases,
) -> AnalysisResponse:
    try:
        view = await use_cases.cancel_analysis(analysis_id, session.owner_hash)
    except AnalysisApplicationError as exc:
        raise analysis_application_error(exc) from exc
    return AnalysisResponse.from_view(view)
