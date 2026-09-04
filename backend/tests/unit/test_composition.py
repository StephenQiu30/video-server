from pathlib import Path

import pytest
from app.core.config import Settings
from app.infrastructure.realtime import RabbitMqRealtimeConsumer
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def disable_external_realtime(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_op(_consumer: RabbitMqRealtimeConsumer) -> None:
        return None

    monkeypatch.setattr(RabbitMqRealtimeConsumer, "start", no_op)
    monkeypatch.setattr(RabbitMqRealtimeConsumer, "close", no_op)


def test_non_test_app_wires_download_use_cases(tmp_path: Path) -> None:
    settings = Settings(
        app_env="development",
        frontend_dist_dir=tmp_path / "missing",
        runner_base_url="http://runner.test",
        valkey_url="redis://127.0.0.1:6379/0",
        _env_file=None,
    )
    application = create_app(settings)

    with TestClient(application) as client:
        assert application.state.download_use_cases is not None
        assert application.state.analysis_use_cases is not None
        assert application.state.auth_service is not None
        assert client.get("/health/live").status_code == 200


def test_non_test_app_wires_runtime_readiness_into_the_route(tmp_path: Path) -> None:
    settings = Settings(
        app_env="development",
        frontend_dist_dir=tmp_path / "missing",
        runner_base_url="http://runner.test",
        valkey_url="redis://127.0.0.1:6379/0",
        _env_file=None,
    )
    application = create_app(settings)

    async def unavailable() -> bool:
        return False

    application.state.readiness_probe.check = unavailable
    with TestClient(application) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503


def test_test_app_leaves_download_use_cases_injectable(tmp_path: Path) -> None:
    application = create_app(
        Settings(app_env="test", frontend_dist_dir=tmp_path / "missing")
    )

    with TestClient(application) as client:
        response = client.post(
            "/api/inspections",
            headers={"Idempotency-Key": "inspect-1"},
            json={
                "source": {
                    "kind": "public_url",
                    "url": "https://media.example/video",
                }
            },
        )

    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"
