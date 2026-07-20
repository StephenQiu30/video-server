# ruff: noqa: B008
"""Liveness and dependency readiness operations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from src.api.dependencies import get_readiness_checker, maybe_await
from src.core.errors import AppError

router = APIRouter(prefix="/health", tags=["health"])


class Health(dict[str, Any]):
    """A tiny response type kept as a plain JSON object for OpenAPI stability."""


@router.get("/live", operation_id="getLiveness", status_code=200)
async def get_liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", operation_id="getReadiness", status_code=200)
async def get_readiness(
    request: Request,
    response: Response,
    checker: Any = Depends(get_readiness_checker),
) -> dict[str, Any]:
    """Return 503 when any configured dependency probe is unavailable."""

    if checker is None:
        # The composition root installs the real PostgreSQL/RabbitMQ/MinIO
        # checker.  No checker means readiness cannot honestly be claimed.
        response.status_code = 503
        return {
            "status": "not_ready",
            "dependencies": {
                "database": "unknown",
                "rabbitmq": "unknown",
                "minio": "unknown",
            },
        }
    try:
        result = await maybe_await(checker())
    except Exception as exc:
        raise AppError(
            "DEPENDENCY_UNAVAILABLE",
            "A required service is not ready.",
            status_code=503,
        ) from exc
    if isinstance(result, bool):
        result = {"status": "ok" if result else "not_ready"}
    if not isinstance(result, dict):
        result = {"status": "ok"}
    ready = result.get("status") in ("ok", "ready", True)
    if not ready:
        response.status_code = 503
    return result


__all__ = ["router"]
