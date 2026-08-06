"""Liveness and dependency-aware readiness endpoints."""

from typing import Protocol, cast

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["system"])


@router.get("/live")
async def live() -> dict[str, str]:
    """Report process liveness without exposing configuration."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    """Reject traffic when any configured runtime dependency is unavailable."""
    dependency = getattr(request.app.state, "readiness_probe", None)
    if dependency is not None:
        probe = cast("ReadinessProbe", dependency)
        if not await probe.check():
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "service": "api"},
            )
    return JSONResponse(content={"status": "ok", "service": "api"})


class ReadinessProbe(Protocol):
    async def check(self) -> bool: ...
