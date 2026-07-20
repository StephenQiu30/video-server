# ruff: noqa: B008
"""Media inspection operation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from src.api.dependencies import (
    SessionIdentity,
    get_media_service,
    get_or_create_session_identity,
    get_request_settings,
    maybe_await,
    set_new_session_cookie,
    verify_post_origin,
)
from src.core.config import Settings
from src.core.errors import AppError, ProblemDetails
from src.media.schemas import InspectedMedia, InspectMediaRequest
from src.media.yt_dlp import (
    MediaExtractionError,
    MediaInspectTimeout,
    MediaLimitError,
    UnsupportedMediaError,
)

router = APIRouter(prefix="/api/v1/media", tags=["media"])


async def _invoke(service: Any, names: tuple[str, ...], **kwargs: Any) -> Any:
    for name in names:
        method = getattr(service, name, None)
        if callable(method):
            return await maybe_await(method(**kwargs))
    if callable(service):
        return await maybe_await(service(**kwargs))
    raise AppError(
        "SERVICE_NOT_READY", "The media service is not ready.", status_code=503
    )


@router.post(
    "/inspect",
    operation_id="inspectMedia",
    response_model=InspectedMedia,
    status_code=200,
    responses={
        400: {"model": ProblemDetails},
        403: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        503: {"model": ProblemDetails},
    },
)
async def inspect_media(
    payload: InspectMediaRequest,
    request: Request,
    response: Response,
    _: None = Depends(verify_post_origin),
    settings: Settings = Depends(get_request_settings),
    identity: SessionIdentity = Depends(get_or_create_session_identity),
    service: Any = Depends(get_media_service),
) -> InspectedMedia:
    """Inspect one public video URL and establish an anonymous session."""

    try:
        result = await _invoke(
            service,
            ("inspect_media", "inspect_source", "inspect"),
            url=payload.url,
            owner_token_hash=identity.token_hash,
        )
    except AppError:
        raise
    except MediaInspectTimeout as exc:
        raise AppError(
            "RESOURCE_LIMIT_EXCEEDED",
            "The media inspection timed out.",
            status_code=422,
        ) from exc
    except MediaLimitError as exc:
        raise AppError(
            "RESOURCE_LIMIT_EXCEEDED",
            "The media exceeds the configured limit.",
            status_code=422,
        ) from exc
    except UnsupportedMediaError as exc:
        reason = str(exc).lower()
        if any(item in reason for item in ("url", "public address", "http(s)")):
            code, detail, status = (
                "URL_FORBIDDEN",
                "The URL is not allowed by the public media policy.",
                403,
            )
        elif "drm" in reason:
            code, detail, status = (
                "VIDEO_DRM_PROTECTED",
                "DRM-protected media is not supported.",
                422,
            )
        else:
            code, detail, status = (
                "VIDEO_UNSUPPORTED",
                "The video source is not supported.",
                422,
            )
        raise AppError(code, detail, status_code=status) from exc
    except MediaExtractionError as exc:
        raise AppError(
            "VIDEO_PARSE_FAILED",
            "The video URL could not be parsed.",
            status_code=422,
        ) from exc
    except ValueError as exc:
        raise AppError(
            "VIDEO_PARSE_FAILED",
            "The video URL could not be parsed.",
            status_code=422,
        ) from exc
    except Exception as exc:
        raise AppError(
            "VIDEO_PARSE_FAILED",
            "The video URL could not be parsed.",
            status_code=422,
        ) from exc
    if result is None:
        raise AppError(
            "VIDEO_PARSE_FAILED",
            "The video URL could not be parsed.",
            status_code=422,
        )
    set_new_session_cookie(identity, response, settings)
    return InspectedMedia.from_model(result)


__all__ = ["router"]
