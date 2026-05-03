import json

from app.routers import health


def test_ready_returns_ok_when_all_checks_pass(monkeypatch) -> None:
    monkeypatch.setattr(health, "_check_database", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_redis", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_queue", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_storage", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_media_tools", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_download_work_dir", lambda: {"ok": True})

    response = health.ready()
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["status"] == "ok"


def test_ready_returns_degraded_when_dependency_fails(monkeypatch) -> None:
    monkeypatch.setattr(health, "_check_database", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_redis", lambda: {"ok": False, "message": "connection refused"})
    monkeypatch.setattr(health, "_check_queue", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_storage", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_media_tools", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_download_work_dir", lambda: {"ok": True})

    response = health.ready()
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["checks"]["redis"]["ok"] is False


def test_ready_returns_degraded_when_media_tools_are_missing(monkeypatch) -> None:
    monkeypatch.setattr(health, "_check_database", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_redis", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_queue", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_storage", lambda: {"ok": True})
    monkeypatch.setattr(health, "_check_media_tools", lambda: {"ok": False})
    monkeypatch.setattr(health, "_check_download_work_dir", lambda: {"ok": True})

    response = health.ready()
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["checks"]["media_tools"]["ok"] is False
