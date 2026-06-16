from fastapi.testclient import TestClient

from app.main import create_app


def test_response_includes_generated_request_id() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.headers["X-Request-ID"]


def test_response_reuses_incoming_request_id() -> None:
    client = TestClient(create_app())

    response = client.get("/health", headers={"X-Request-ID": "req-test-123"})

    assert response.headers["X-Request-ID"] == "req-test-123"


def test_security_headers_are_present() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Request-Duration-Ms"].isdigit()


def test_failure_response_includes_request_id() -> None:
    """Failure envelope must include request_id for traceability."""
    client = TestClient(create_app())

    response = client.get("/nonexistent-path")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "request_id" in body
    assert body["request_id"]
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_failure_response_reuses_incoming_request_id() -> None:
    """When client sends X-Request-ID, failure envelope reuses it."""
    client = TestClient(create_app())

    response = client.get("/nonexistent-path", headers={"X-Request-ID": "trace-abc-123"})

    assert response.status_code == 404
    body = response.json()
    assert body["request_id"] == "trace-abc-123"
    assert response.headers["X-Request-ID"] == "trace-abc-123"
