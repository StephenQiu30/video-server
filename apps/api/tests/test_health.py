import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.routers import health


def test_app_lifespan_starts_with_test_client() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200


def _mock_all_checks(monkeypatch) -> None:
    """Set all health checks to passing."""
    monkeypatch.setattr(health, "_check_database", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_redis", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_queue", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_queue_consumer", lambda: {"ok": True, "ready": True})
    monkeypatch.setattr(health, "_check_storage", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_media_tools", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_download_work_dir", lambda: {"ok": True})


def test_ready_returns_ok_when_all_checks_pass(monkeypatch) -> None:
    _mock_all_checks(monkeypatch)

    response = health.ready()
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["status"] == "ok"


def test_ready_returns_degraded_when_dependency_fails(monkeypatch) -> None:
    _mock_all_checks(monkeypatch)
    monkeypatch.setattr(health, "_check_redis", lambda: {"ok": False, "message": "connection refused"})

    response = health.ready()
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["checks"]["redis"]["ok"] is False


def test_ready_returns_degraded_when_media_tools_are_missing(monkeypatch) -> None:
    _mock_all_checks(monkeypatch)
    monkeypatch.setattr(health, "_check_media_tools", lambda: {"ok": False})

    response = health.ready()
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["checks"]["media_tools"]["ok"] is False


def test_ready_returns_degraded_when_queue_consumer_is_down(monkeypatch) -> None:
    _mock_all_checks(monkeypatch)
    monkeypatch.setattr(health, "_check_queue_consumer", lambda: {"ok": False, "ready": False})

    response = health.ready()
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["checks"]["queue_consumer"]["ok"] is False


def test_queue_consumer_check_reports_worker_thread_status(monkeypatch) -> None:
    """_check_queue_consumer reads the runtime worker thread state."""
    import app.runtime as runtime

    monkeypatch.setattr(runtime, "_worker_ready", True)
    monkeypatch.setattr(runtime, "_worker_thread", _FakeThread(alive=True))

    result = health._check_queue_consumer()

    assert result["ok"] is True
    assert result["ready"] is True


def test_queue_consumer_check_fails_when_thread_dead(monkeypatch) -> None:
    """_check_queue_consumer reports failure when the worker thread is not alive."""
    import app.runtime as runtime

    monkeypatch.setattr(runtime, "_worker_ready", True)
    monkeypatch.setattr(runtime, "_worker_thread", _FakeThread(alive=False))

    result = health._check_queue_consumer()

    assert result["ok"] is False


class _FakeThread:
    def __init__(self, alive: bool) -> None:
        self._alive = alive

    def is_alive(self) -> bool:
        return self._alive
