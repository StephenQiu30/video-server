"""Bounded dependency probes used by the API readiness endpoint."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import aio_pika
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings

AsyncCheck = Callable[[], Awaitable[None]]


class RuntimeReadiness:
    def __init__(
        self,
        checks: tuple[AsyncCheck, ...],
        client: httpx.AsyncClient,
        *,
        timeout_seconds: float,
    ) -> None:
        self._checks = checks
        self._client = client
        self._timeout_seconds = timeout_seconds

    async def check(self) -> bool:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                results = await asyncio.gather(
                    *(check() for check in self._checks),
                    return_exceptions=True,
                )
        except TimeoutError:
            return False
        return all(result is None for result in results)

    async def close(self) -> None:
        await self._client.aclose()


def build_runtime_readiness(
    settings: Settings,
    engine: AsyncEngine,
    *,
    client: httpx.AsyncClient | None = None,
    valkey_check: AsyncCheck | None = None,
) -> RuntimeReadiness:
    http_client = client or httpx.AsyncClient(
        timeout=settings.readiness_timeout_seconds,
        follow_redirects=False,
    )
    runner_url = f"{settings.runner_base_url.rstrip('/')}/health/live"
    minio_scheme = "https" if settings.minio_internal_secure else "http"
    minio_url = (
        f"{minio_scheme}://{settings.minio_endpoint.rstrip('/')}/minio/health/live"
    )

    async def database_check() -> None:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def http_check(url: str) -> None:
        response = await http_client.get(url)
        response.raise_for_status()

    async def rabbitmq_check() -> None:
        connection = await aio_pika.connect(
            settings.rabbitmq_url,
            timeout=settings.readiness_timeout_seconds,
            client_properties={"connection_name": "video-server-api-readiness"},
        )
        await connection.close()

    checks: list[AsyncCheck] = [
        database_check,
        lambda: http_check(runner_url),
        lambda: http_check(minio_url),
        rabbitmq_check,
    ]
    if valkey_check is not None:
        checks.append(valkey_check)
    return RuntimeReadiness(
        tuple(checks),
        http_client,
        timeout_seconds=settings.readiness_timeout_seconds,
    )
