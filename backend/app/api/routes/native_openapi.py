"""App-only OpenAPI document used to generate native clients."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.openapi.utils import get_openapi

from app.api.routes.native_auth import router as native_auth_router

router = APIRouter(prefix="/api/app/v1")


def build_native_openapi() -> dict[str, Any]:
    return get_openapi(
        title="帧取 App API",
        version="1.0.0",
        description="Flutter iOS 与 Android 客户端使用的冻结契约来源。",
        routes=native_auth_router.routes,
    )


@router.get("/openapi.json", include_in_schema=False)
async def get_native_openapi() -> dict[str, Any]:
    return build_native_openapi()
