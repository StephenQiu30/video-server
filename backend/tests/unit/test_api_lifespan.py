from unittest.mock import AsyncMock, Mock

import pytest
from app import main
from app.core import lifespan
from app.core.config import Settings
from app.core.runtime import ApiRuntime, ApiServices
from fastapi.testclient import TestClient


def test_app_factory_does_not_build_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    build = Mock(side_effect=AssertionError("resources built outside lifespan"))
    monkeypatch.setattr(lifespan, "build_api_runtime", build)
    application = main.create_app(Settings(app_env="development", _env_file=None))
    assert application.openapi()["paths"]
    build.assert_not_called()


def test_lifespan_builds_starts_and_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = Mock(start=AsyncMock(), close=AsyncMock())
    build = Mock(return_value=runtime)
    monkeypatch.setattr(lifespan, "build_api_runtime", build)
    application = main.create_app(Settings(app_env="development", _env_file=None))
    with TestClient(application) as client:
        build.assert_called_once()
        runtime.start.assert_awaited_once()
        runtime.close.assert_not_awaited()
        assert client.get("/health/live").status_code == 200
    runtime.close.assert_awaited_once()


async def test_runtime_cleanup_continues_after_consumer_close_fails() -> None:
    engine = Mock(dispose=AsyncMock())
    runner = Mock(close=AsyncMock())
    sessions = Mock(close=AsyncMock())
    consumer = Mock(close=AsyncMock(side_effect=RuntimeError("close failed")))
    readiness = Mock(close=AsyncMock())
    limiter = Mock(close=AsyncMock())
    runtime = ApiRuntime(
        services=ApiServices(readiness_probe=readiness, rate_limiter=limiter),
        engine=engine,
        runner=runner,
        auth_session_store=sessions,
        realtime_consumer=consumer,
    )
    with pytest.raises(RuntimeError, match="close failed"):
        await runtime.close()
    for resource in (runner, sessions, readiness, limiter):
        resource.close.assert_awaited_once()
    engine.dispose.assert_awaited_once()


def test_injected_runtime_remains_owned_by_the_caller() -> None:
    runtime = Mock(services=ApiServices(), start=AsyncMock(), close=AsyncMock())
    application = main.create_app(Settings(app_env="test"), runtime=runtime)
    with TestClient(application):
        assert application.state.services is runtime.services
    runtime.start.assert_not_awaited()
    runtime.close.assert_not_awaited()


def test_startup_failure_still_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = Mock(
        start=AsyncMock(side_effect=RuntimeError("startup failed")), close=AsyncMock()
    )
    monkeypatch.setattr(lifespan, "build_api_runtime", Mock(return_value=runtime))
    application = main.create_app(Settings(app_env="development", _env_file=None))
    with pytest.raises(RuntimeError, match="startup failed"), TestClient(application):
        pass
    runtime.close.assert_awaited_once()
