# ruff: noqa: B008
"""Download creation, status, and presigned URL operations."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from src.api.dependencies import (
    SessionIdentity,
    get_download_service,
    get_queue_publisher,
    get_request_settings,
    get_required_session_identity,
    maybe_await,
    verify_post_origin,
)
from src.core.config import Settings
from src.core.errors import AppError, ProblemDetails
from src.downloads.schemas import (
    CreateDownloadRequest,
    DownloadJob,
    DownloadUrl,
)

router = APIRouter(prefix="/api/v1/downloads", tags=["downloads"])


async def _invoke(service: Any, names: tuple[str, ...], **kwargs: Any) -> Any:
    for name in names:
        method = getattr(service, name, None)
        if callable(method):
            return await maybe_await(method(**kwargs))
    if callable(service):
        return await maybe_await(service(**kwargs))
    raise AppError(
        "SERVICE_NOT_READY", "The download service is not ready.", status_code=503
    )


def _job_and_created(value: Any) -> tuple[Any, bool]:
    """Accept the explicit ``(job, created)`` adapter result or a plain job."""

    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[1], bool):
        return value[0], value[1]
    if isinstance(value, dict) and "job" in value:
        return value["job"], bool(value.get("created", True))
    return value, True


def _translate_repository_error(exc: Exception) -> AppError:
    name = type(exc).__name__
    message = str(exc).lower()
    if "conflict" in name.lower() or "already" in message:
        return AppError(
            "IDEMPOTENCY_CONFLICT",
            "The client request id conflicts with an existing download.",
            status_code=409,
        )
    if "notfound" in name.lower() or "not found" in message:
        return AppError(
            "RESOURCE_NOT_FOUND",
            "The requested resource was not found.",
            status_code=404,
        )
    return AppError(
        "DOWNLOAD_FAILED",
        "The download request could not be processed.",
        status_code=422,
    )


@router.post(
    "",
    operation_id="createDownload",
    response_model=DownloadJob,
    status_code=202,
    responses={
        200: {"model": DownloadJob},
        400: {"model": ProblemDetails},
        403: {"model": ProblemDetails},
        409: {"model": ProblemDetails},
        410: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        503: {"model": ProblemDetails},
    },
)
async def create_download(
    payload: CreateDownloadRequest,
    request: Request,
    response: Response,
    _: None = Depends(verify_post_origin),
    settings: Settings = Depends(get_request_settings),
    identity: SessionIdentity = Depends(get_required_session_identity),
    service: Any = Depends(get_download_service),
    publisher: Any | None = Depends(get_queue_publisher),
) -> DownloadJob:
    del request, settings
    try:
        result = await _invoke(
            service,
            ("create_download", "create_job"),
            owner_token_hash=identity.token_hash,
            source_id=payload.source_id,
            format_id=payload.format_id,
            client_request_id=payload.client_request_id,
        )
    except AppError:
        raise
    except Exception as exc:
        raise _translate_repository_error(exc) from exc
    job_value, created = _job_and_created(result)
    job = DownloadJob.from_model(job_value)
    if created and publisher is not None:
        try:
            publish = getattr(publisher, "publish", None)
            if not callable(publish):
                raise RuntimeError("publisher has no publish method")
            await maybe_await(publish(uuid.UUID(str(job.id))))
        except Exception as exc:
            raise AppError(
                "QUEUE_PUBLISH_FAILED",
                "The download could not be queued.",
                status_code=503,
            ) from exc
    response.status_code = 202 if created else 200
    return job


@router.get(
    "/{job_id}",
    operation_id="getDownload",
    response_model=DownloadJob,
    status_code=200,
    responses={
        400: {"model": ProblemDetails},
        403: {"model": ProblemDetails},
        404: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
    },
)
async def get_download(
    job_id: uuid.UUID,
    identity: SessionIdentity = Depends(get_required_session_identity),
    service: Any = Depends(get_download_service),
) -> DownloadJob:
    try:
        result = await _invoke(
            service,
            ("get_download", "get_job"),
            owner_token_hash=identity.token_hash,
            job_id=job_id,
        )
    except AppError:
        raise
    except Exception as exc:
        raise _translate_repository_error(exc) from exc
    if result is None:
        raise AppError(
            "RESOURCE_NOT_FOUND",
            "The requested download was not found.",
            status_code=404,
        )
    return DownloadJob.from_model(result)


@router.post(
    "/{job_id}/download-url",
    operation_id="createDownloadUrl",
    response_model=DownloadUrl,
    status_code=200,
    responses={
        400: {"model": ProblemDetails},
        403: {"model": ProblemDetails},
        404: {"model": ProblemDetails},
        409: {"model": ProblemDetails},
        410: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        503: {"model": ProblemDetails},
    },
)
async def create_download_url(
    job_id: uuid.UUID,
    _: None = Depends(verify_post_origin),
    identity: SessionIdentity = Depends(get_required_session_identity),
    service: Any = Depends(get_download_service),
) -> DownloadUrl:
    try:
        result = await _invoke(
            service,
            ("create_download_url", "download_url", "get_download_url"),
            owner_token_hash=identity.token_hash,
            job_id=job_id,
        )
    except AppError:
        raise
    except Exception as exc:
        raise _translate_repository_error(exc) from exc
    if result is None:
        raise AppError(
            "JOB_NOT_READY", "The download is not ready yet.", status_code=409
        )
    return (
        result
        if isinstance(result, DownloadUrl)
        else DownloadUrl.model_validate(result)
    )


__all__ = ["router"]
