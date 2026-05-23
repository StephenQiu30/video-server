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
