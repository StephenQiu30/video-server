from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.core.errors import AppError
from app.main import create_app
from fastapi.testclient import TestClient


def test_app_error_uses_stable_problem_details(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "missing"))

    @app.get("/api/test-error")
    async def test_error() -> None:
        raise AppError(
            status=409,
            code="job_conflict",
            title="Job conflict",
            detail="The job cannot transition from its current state.",
        )

    with TestClient(app) as client:
        response = client.get("/api/test-error")

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "urn:video-server:error:job_conflict",
        "title": "Job conflict",
        "status": 409,
        "detail": "The job cannot transition from its current state.",
        "code": "job_conflict",
        "instance": "/api/test-error",
    }
