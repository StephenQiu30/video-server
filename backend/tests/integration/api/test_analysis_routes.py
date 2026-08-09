from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import AnalysisUseCases
from app.application.analysis import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    AnalysisJobView,
)
from app.application.auth import CurrentUser, UserRole
from app.core.config import Settings
from app.domain.analysis import AnalysisStatus
from app.main import create_app
from fastapi.testclient import TestClient

NOW = datetime(2026, 8, 6, 10, tzinfo=UTC)
DOWNLOAD_ID = UUID("44444444-4444-4444-8444-444444444444")
ANALYSIS_ID = UUID("55555555-5555-4555-8555-555555555555")
RESULT = {
    "schema_version": "visual-analysis.v1",
    "language": "zh-CN",
    "title": "可验证视觉分析",
    "summary": {"text": "摘要", "evidence_shot_ids": ["shot-1"]},
    "media": {"duration_ms": 1_000, "container": "mp4", "size_bytes": 100},
    "shot_count": 1,
    "shots": [
        {
            "id": "shot-1",
            "index": 1,
            "start_ms": 0,
            "end_ms": 1_000,
            "representative_frame_ms": 500,
            "description": "开场画面",
            "transition_in": "none",
            "shot_size": "wide",
            "camera_motion": "static",
            "visual_tags": ["开场"],
            "asset_ids": ["asset-1"],
        }
    ],
    "highlights": [],
    "assets": [
        {
            "id": "asset-1",
            "type": "logo",
            "label": "示例标志",
            "description": "画面标志",
            "first_seen_ms": 0,
            "evidence_shot_ids": ["shot-1"],
        }
    ],
}
TEST_USER = CurrentUser(
    id=DOWNLOAD_ID,
    username="video_user",
    email="user@example.com",
    role=UserRole.USER,
    created_at=NOW,
    updated_at=NOW,
)


class StubUseCase:
    def __init__(self, result: AnalysisJobView) -> None:
        self.result = result
        self.error: AnalysisApplicationError | None = None
        self.calls: list[tuple[object, ...]] = []

    async def __call__(self, *args: object) -> AnalysisJobView:
        self.calls.append(args)
        if self.error is not None:
            raise self.error
        return self.result


def analysis_view(
    status: AnalysisStatus = AnalysisStatus.QUEUED,
    *,
    result: dict[str, object] | None = None,
) -> AnalysisJobView:
    return AnalysisJobView(
        id=ANALYSIS_ID,
        profile="visual-shot-v1",
        output_language="zh-CN",
        status=status,
        stage=None,
        progress=100 if status is AnalysisStatus.SUCCEEDED else 0,
        attempt=1 if status is AnalysisStatus.SUCCEEDED else 0,
        error_code=None,
        created_at=NOW,
        updated_at=NOW,
        finished_at=NOW if status is AnalysisStatus.SUCCEEDED else None,
        result=result,
    )


def client(tmp_path: Path) -> tuple[TestClient, dict[str, StubUseCase]]:
    application = create_app(
        Settings(app_env="test", frontend_dist_dir=tmp_path / "none")
    )
    queued = analysis_view()
    stubs = {
        "create": StubUseCase(queued),
        "get": StubUseCase(queued),
        "cancel": StubUseCase(
            replace(queued, status=AnalysisStatus.CANCELLED, finished_at=NOW)
        ),
    }
    application.state.analysis_use_cases = AnalysisUseCases(
        create_analysis=stubs["create"],
        get_analysis=stubs["get"],
        cancel_analysis=stubs["cancel"],
    )
    application.dependency_overrides[get_current_user] = lambda: TEST_USER
    return TestClient(application), stubs


def test_analysis_service_must_be_wired(tmp_path: Path) -> None:
    application = create_app(
        Settings(app_env="test", frontend_dist_dir=tmp_path / "none")
    )
    with TestClient(application) as test_client:
        response = test_client.get(f"/api/analyses/{ANALYSIS_ID}")

    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


def test_analysis_routes_share_owner_and_never_expose_internal_ids(
    tmp_path: Path,
) -> None:
    test_client, stubs = client(tmp_path)
    with test_client:
        created = test_client.post(
            f"/api/downloads/{DOWNLOAD_ID}/analyses",
            headers={"Idempotency-Key": "analysis-1"},
            json={"profile": "visual-shot-v1", "output_language": "zh-CN"},
        )
        fetched = test_client.get(f"/api/analyses/{ANALYSIS_ID}")
        cancelled = test_client.post(f"/api/analyses/{ANALYSIS_ID}/cancel")

    assert created.status_code == 201
    assert created.headers["location"] == f"/api/analyses/{ANALYSIS_ID}"
    assert fetched.status_code == cancelled.status_code == 200
    assert created.json()["result"] is None
    assert cancelled.json()["status"] == "cancelled"
    assert "artifact_id" not in created.text
    owners = (
        stubs["create"].calls[0][1],
        stubs["get"].calls[0][1],
        stubs["cancel"].calls[0][1],
    )
    assert len(set(owners)) == 1


def test_succeeded_analysis_returns_only_strict_structured_result(
    tmp_path: Path,
) -> None:
    test_client, stubs = client(tmp_path)
    stubs["get"].result = analysis_view(
        AnalysisStatus.SUCCEEDED,
        result=RESULT,
    )
    with test_client:
        response = test_client.get(f"/api/analyses/{ANALYSIS_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["shot_count"] == 1
    assert payload["result"]["assets"][0]["evidence_shot_ids"] == ["shot-1"]
    assert "schema_version" not in payload["result"]
    assert "transcript" not in response.text
    assert "provider" not in response.text


def test_analysis_creation_rejects_invalid_or_extra_input(tmp_path: Path) -> None:
    test_client, stubs = client(tmp_path)
    requests = (
        ({}, {"profile": "visual-shot-v1", "output_language": "zh-CN"}),
        (
            {"Idempotency-Key": "analysis-1"},
            {"profile": "legacy", "output_language": "zh-CN"},
        ),
        (
            {"Idempotency-Key": "analysis-1"},
            {"profile": "visual-shot-v1", "output_language": "not a language"},
        ),
        (
            {"Idempotency-Key": "analysis-1"},
            {
                "profile": "visual-shot-v1",
                "output_language": "zh-CN",
                "prompt": "leak",
            },
        ),
    )
    with test_client:
        responses = [
            test_client.post(
                f"/api/downloads/{DOWNLOAD_ID}/analyses",
                headers=headers,
                json=body,
            )
            for headers, body in requests
        ]

    assert {response.status_code for response in responses} == {422}
    assert stubs["create"].calls == []


def test_analysis_errors_are_problem_details(tmp_path: Path) -> None:
    test_client, stubs = client(tmp_path)
    with test_client:
        for code, expected_status in (
            (AnalysisApplicationErrorCode.NOT_FOUND, 404),
            (AnalysisApplicationErrorCode.ARTIFACT_NOT_READY, 409),
            (AnalysisApplicationErrorCode.IDEMPOTENCY_CONFLICT, 409),
            (AnalysisApplicationErrorCode.SERVICE_UNAVAILABLE, 503),
        ):
            stubs["create"].error = AnalysisApplicationError(code)
            response = test_client.post(
                f"/api/downloads/{DOWNLOAD_ID}/analyses",
                headers={"Idempotency-Key": "analysis-1"},
                json={"profile": "visual-shot-v1", "output_language": "zh-CN"},
            )
            assert response.status_code == expected_status
            assert response.headers["content-type"].startswith(
                "application/problem+json"
            )
            assert response.json()["code"] == code.value
            assert response.json()["instance"].endswith(f"/{DOWNLOAD_ID}/analyses")
