"""Liveness and dependency-aware readiness endpoints."""

from typing import Protocol, cast

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.schemas.system import LivenessResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["system"])


@router.get(
    "/live",
    operation_id="getLiveness",
    response_model=LivenessResponse,
    summary="检查进程存活状态",
)
async def live() -> dict[str, str]:
    """Report process liveness without exposing configuration."""
    return {"status": "ok"}


@router.get(
    "/ready",
    operation_id="getReadiness",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "运行依赖不可用"}},
    summary="检查服务就绪状态",
)
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
