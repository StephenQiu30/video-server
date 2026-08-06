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
from app.api.schemas import (
    DownloadRequest,
    DownloadResponse,
    DownloadUrlResponse,
)
from app.application.downloads import ApplicationError
from app.core.session import AnonymousSession

router = APIRouter(prefix="/api/v1/downloads", tags=["downloads"])
Session = Annotated[AnonymousSession, Depends(get_anonymous_session)]
UseCases = Annotated[DownloadUseCases, Depends(get_download_use_cases)]
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128),
]


@router.post(
    "",
    response_model=DownloadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_download(
    body: DownloadRequest,
    idempotency_key: IdempotencyKey,
    session: Session,
    use_cases: UseCases,
) -> DownloadResponse:
    try:
        view = await use_cases.create_download(
            body.inspection_id,
            body.format_id,
            session.owner_hash,
            idempotency_key,
        )
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadResponse.from_view(view)


@router.get("/{job_id}", response_model=DownloadResponse)
async def get_download(
    job_id: UUID,
    session: Session,
    use_cases: UseCases,
) -> DownloadResponse:
    try:
        view = await use_cases.get_download(job_id, session.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadResponse.from_view(view)


@router.post("/{job_id}/cancel", response_model=DownloadResponse)
async def cancel_download(
    job_id: UUID,
    session: Session,
    use_cases: UseCases,
) -> DownloadResponse:
    try:
        view = await use_cases.cancel_download(job_id, session.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadResponse.from_view(view)


@router.post("/{job_id}/download-url", response_model=DownloadUrlResponse)
async def issue_download_url(
    job_id: UUID,
    session: Session,
    use_cases: UseCases,
) -> DownloadUrlResponse:
    try:
        view = await use_cases.issue_download_url(job_id, session.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadUrlResponse.from_view(view)
