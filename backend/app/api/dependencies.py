"""Request-scoped dependencies shared by API routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request, Response

from app.application.analysis import CancelAnalysis, CreateAnalysis, GetAnalysis
from app.application.downloads import (
    CancelDownload,
    CreateDownload,
    GetDownload,
    GetInspection,
    InspectMedia,
    IssueDownloadUrl,
)
from app.core.config import Settings
from app.core.errors import AppError
from app.core.session import AnonymousSession, SessionError, SessionManager


def get_runtime_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


@dataclass(frozen=True, slots=True)
class DownloadUseCases:
    inspect_media: InspectMedia
    get_inspection: GetInspection
    create_download: CreateDownload
    get_download: GetDownload
    cancel_download: CancelDownload
    issue_download_url: IssueDownloadUrl


@dataclass(frozen=True, slots=True)
class AnalysisUseCases:
    create_analysis: CreateAnalysis
    get_analysis: GetAnalysis
    cancel_analysis: CancelAnalysis


def get_download_use_cases(request: Request) -> DownloadUseCases:
    container = getattr(request.app.state, "download_use_cases", None)
    if container is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The download service is not available.",
        )
    return cast(DownloadUseCases, container)


def get_analysis_use_cases(request: Request) -> AnalysisUseCases:
    container = getattr(request.app.state, "analysis_use_cases", None)
    if container is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The analysis service is not available.",
        )
    return cast(AnalysisUseCases, container)


def get_anonymous_session(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> AnonymousSession:
    manager = SessionManager(
        settings.session_secret.get_secret_value().encode(),
        ttl_seconds=settings.session_ttl_seconds,
    )
    token = request.cookies.get(settings.session_cookie_name)
    session: AnonymousSession | None = None
    if token:
        try:
            session = manager.verify(token)
        except SessionError:
            session = None
    if session is None:
        session = manager.issue()
        response.set_cookie(
            key=settings.session_cookie_name,
            value=session.token,
            max_age=settings.session_ttl_seconds,
            httponly=True,
            secure=settings.app_env in {"staging", "production"},
            samesite="lax",
            path="/",
        )
    return session
