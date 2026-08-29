from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aio_pika
import httpx
import pytest
from app.core.config import Settings
from app.infrastructure.readiness import build_runtime_readiness
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class FakeConnection:
    async def close(self) -> None:
        return None


@pytest.fixture
def rabbitmq_is_available(monkeypatch: pytest.MonkeyPatch) -> None:
    async def connect(
        url: str,
        *,
        timeout: float,
        client_properties: dict[str, str],
    ) -> FakeConnection:
        assert url == "amqp://user:redacted@rabbit.test:5672/"
        assert timeout == 1
        assert client_properties["connection_name"] == "video-server-api-readiness"
        return FakeConnection()

    monkeypatch.setattr(aio_pika, "connect", connect)


@asynccontextmanager
async def runtime_probe(
    handler: httpx.AsyncBaseTransport,
    engine: AsyncEngine,
    *,
    operator_runners: dict[str, str] | None = None,
) -> AsyncIterator[Any]:
    client = httpx.AsyncClient(transport=handler)
    settings = Settings(
        app_env="test",
        database_url=str(engine.url),
        rabbitmq_url="amqp://user:redacted@rabbit.test:5672/",
        runner_base_url="http://runner.test",
        runner_operator_base_urls=operator_runners or {},
        minio_endpoint="minio.test:9000",
        readiness_timeout_seconds=1,
    )
    probe = build_runtime_readiness(settings, engine, client=client)
    try:
        yield probe
    finally:
        await probe.close()


@pytest.mark.usefixtures("rabbitmq_is_available")
async def test_runtime_readiness_checks_database_runner_minio_and_rabbitmq(
    postgres_engine: AsyncEngine,
) -> None:
    async def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path in {"/health/ready", "/minio/health/live"}
        return httpx.Response(200)

    async with runtime_probe(httpx.MockTransport(respond), postgres_engine) as probe:
        assert await probe.check() is True


@pytest.mark.usefixtures("rabbitmq_is_available")
async def test_runtime_readiness_fails_closed_without_exposing_dependency_error(
    postgres_engine: AsyncEngine,
) -> None:
    async def respond(request: httpx.Request) -> httpx.Response:
        status = 503 if request.url.host == "runner.test" else 200
        return httpx.Response(status)

    async with runtime_probe(httpx.MockTransport(respond), postgres_engine) as probe:
        assert await probe.check() is False


@pytest.mark.usefixtures("rabbitmq_is_available")
async def test_runtime_readiness_does_not_depend_on_optional_operator_runner(
    postgres_engine: AsyncEngine,
) -> None:
    seen: set[str] = set()

    async def respond(request: httpx.Request) -> httpx.Response:
        seen.add(request.url.host or "")
        return httpx.Response(200)

    async with runtime_probe(
        httpx.MockTransport(respond),
        postgres_engine,
        operator_runners={"x": "http://x-runner.test"},
    ) as probe:
        assert await probe.check() is True

    assert "runner.test" in seen
    assert "minio.test" in seen
    assert "x-runner.test" not in seen


@pytest.mark.usefixtures("rabbitmq_is_available")
async def test_runtime_readiness_checks_the_active_postgres_schema(
    postgres_engine: AsyncEngine,
) -> None:
    async with postgres_engine.begin() as connection:
        await connection.execute(text("DROP TABLE document_artifacts CASCADE"))

    async def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with runtime_probe(httpx.MockTransport(respond), postgres_engine) as probe:
        assert await probe.check() is False


@pytest.mark.usefixtures("rabbitmq_is_available")
async def test_runtime_readiness_does_not_depend_on_analysis_worker(
    postgres_engine: AsyncEngine,
) -> None:
    async def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with runtime_probe(httpx.MockTransport(respond), postgres_engine) as probe:
        assert await probe.check() is True
