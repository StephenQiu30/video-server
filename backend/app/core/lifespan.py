"""Own API process resources for exactly one FastAPI lifespan."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.composition import build_api_runtime
from app.core.config import Settings
from app.core.runtime import ApiRuntime


@asynccontextmanager
async def api_lifespan(
    app: FastAPI, settings: Settings, runtime: ApiRuntime | None = None
) -> AsyncIterator[None]:
    owned = runtime is None and settings.app_env != "test"
    configured = build_api_runtime(settings) if owned else runtime
    original_services = app.state.services
    try:
        if configured is not None:
            app.state.services = configured.services
            if owned:
                await configured.start()
        yield
    finally:
        try:
            if owned and configured is not None:
                await configured.close()
        finally:
            app.state.services = original_services
