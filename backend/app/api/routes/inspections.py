from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.api.dependencies import (
    DownloadUseCases,
    get_anonymous_session,
    get_download_use_cases,
)
from app.api.errors import application_error
from app.api.schemas import InspectionRequest, InspectionResponse
from app.application.downloads import ApplicationError
from app.core.session import AnonymousSession

router = APIRouter(prefix="/api/v1/inspections", tags=["inspections"])
Session = Annotated[AnonymousSession, Depends(get_anonymous_session)]
UseCases = Annotated[DownloadUseCases, Depends(get_download_use_cases)]
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128),
]


@router.post(
    "",
    response_model=InspectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def inspect_media(
    body: InspectionRequest,
    idempotency_key: IdempotencyKey,
    session: Session,
    use_cases: UseCases,
) -> InspectionResponse:
    try:
        view = await use_cases.inspect_media(
            body.url, session.owner_hash, idempotency_key
        )
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return InspectionResponse.from_view(view)


@router.get("/{inspection_id}", response_model=InspectionResponse)
async def get_inspection(
    inspection_id: UUID,
    session: Session,
    use_cases: UseCases,
) -> InspectionResponse:
    try:
        view = await use_cases.get_inspection(inspection_id, session.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return InspectionResponse.from_view(view)
