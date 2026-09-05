import pytest
from app.application.quotas import QuotaExceeded
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("storage_quota_exceeded", 429),
        ("daily_task_quota_exceeded", 429),
        ("analysis_budget_exceeded", 429),
        ("service_capacity_exceeded", 503),
    ],
)
def test_admission_failure_uses_problem_details_and_retry_header(code, status):
    app = create_app(Settings(_env_file=None, app_env="test"))

    @app.post("/test-quota")
    async def exhausted():
        raise QuotaExceeded(code, retry_after=123)

    with TestClient(app) as client:
        response = client.post("/test-quota")
    assert response.status_code == status
    assert response.headers["retry-after"] == "123"
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == code
