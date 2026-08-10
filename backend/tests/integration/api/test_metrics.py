from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


class FakeMetrics:
    async def render(self, now: datetime) -> str:
        assert now.tzinfo is UTC
        return 'video_analysis_jobs{state="queued"} 2\n'


def test_internal_metrics_require_scrape_key_and_stay_out_of_openapi(
    tmp_path: Path,
) -> None:
    app = create_app(
        Settings(
            app_env="test",
            frontend_dist_dir=tmp_path / "none",
            metrics_access_key="controlled-metrics-key",
        )
    )
    app.state.operational_metrics = FakeMetrics()
    with TestClient(app) as client:
        assert client.get("/internal/metrics").status_code == 404
        response = client.get(
            "/internal/metrics", headers={"X-Metrics-Key": "controlled-metrics-key"}
        )
        schema = client.get("/openapi.json").json()

    assert response.status_code == 200
    assert response.text == 'video_analysis_jobs{state="queued"} 2\n'
    assert "/internal/metrics" not in schema["paths"]
