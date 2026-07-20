from __future__ import annotations

from fastapi.testclient import TestClient
from src.core.config import Settings
from src.main import create_app


def test_health_endpoint_does_not_expose_configuration() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://video:video@localhost:5432/video",
        rabbitmq_url="amqp://video:video@localhost:5672/",
        minio_endpoint="localhost:9000",
        minio_access_key="video-access",
        minio_secret_key="video-secret",
        minio_bucket="video-artifacts",
        session_secret="a-development-session-secret-with-sufficient-length",
        app_env="test",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "video-secret" not in response.text
