from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.api.auth_dependencies import get_current_user
from app.application.auth import CurrentUser, UserRole
from app.application.downloads import ApplicationError, ApplicationErrorCode
from app.core.config import Settings
from app.domain.downloads import DownloadStatus
from app.main import create_app
from fastapi.testclient import TestClient
from tests.integration.api.fakes import (
    FORMAT_ID,
    INSPECTION_ID,
    JOB_ID,
    StubUseCase,
    use_cases,
)

TEST_USER = CurrentUser(
    id=JOB_ID,
    username="video_user",
    email="user@example.com",
    role=UserRole.USER,
    created_at=datetime(2026, 8, 6, tzinfo=UTC),
    updated_at=datetime(2026, 8, 6, tzinfo=UTC),
)


def client(tmp_path: Path) -> tuple[TestClient, dict[str, StubUseCase]]:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    container, stubs = use_cases()
    app.state.download_use_cases = container
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    return TestClient(app), stubs


def test_download_use_cases_are_resolved_from_app_state(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/inspections",
            headers={"Idempotency-Key": "inspect-1"},
            json={"url": "https://media.example/owned"},
        )

    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


def test_inspection_routes_use_stable_session_and_hide_hints(tmp_path: Path) -> None:
    test_client, stubs = client(tmp_path)
    with test_client:
        created = test_client.post(
            "/api/inspections",
            headers={"Idempotency-Key": "inspect-1"},
            json={"url": "https://media.example/owned"},
        )
        fetched = test_client.get(f"/api/inspections/{INSPECTION_ID}")

    assert created.status_code == 201
    assert fetched.status_code == 200
    payload = created.json()
    assert payload["id"] == str(INSPECTION_ID)
    assert "hints" not in payload["formats"][0]["plan"]
    assert "provider_hints" not in created.text
    create_owner = stubs["inspect"].calls[0][0][1]
    get_owner = stubs["get_inspection"].calls[0][0][1]
    assert create_owner == get_owner
    assert len(str(create_owner)) == 64


def test_download_routes_delegate_with_session_owner(tmp_path: Path) -> None:
    test_client, stubs = client(tmp_path)
    body = {"inspection_id": str(INSPECTION_ID), "format_id": str(FORMAT_ID)}
    with test_client:
        created = test_client.post(
            "/api/downloads",
            headers={"Idempotency-Key": "download-1"},
            json=body,
        )
        fetched = test_client.get(f"/api/downloads/{JOB_ID}")
        cancelled = test_client.post(f"/api/downloads/{JOB_ID}/cancel")
        retried = test_client.post(
            f"/api/downloads/{JOB_ID}/retry",
            headers={"Idempotency-Key": "retry-1"},
        )
        issued = test_client.post(f"/api/downloads/{JOB_ID}/download-url")

    assert created.status_code == 201
    assert created.headers["location"] == f"/api/downloads/{JOB_ID}"
    assert fetched.status_code == cancelled.status_code == issued.status_code == 200
    assert retried.status_code == 201
    assert retried.headers["location"] == f"/api/downloads/{JOB_ID}"
    assert created.json()["status"] == "queued"
    assert cancelled.json()["status"] == "cancelled"
    assert issued.json()["url"] == "https://objects.example/token"
    owners = [
        stubs["create"].calls[0][0][-2],
        *(stubs[name].calls[0][0][-1] for name in ("get", "cancel", "issue_url")),
        stubs["retry"].calls[0][0][-2],
    ]
    assert len(set(owners)) == 1
    assert stubs["retry"].calls[0][0][-1] == "retry-1"


def test_download_history_route_supports_filters_and_returns_public_fields(
    tmp_path: Path,
) -> None:
    test_client, stubs = client(tmp_path)
    with test_client:
        response = test_client.get(
            "/api/downloads/history",
            params={
                "page": 2,
                "page_size": 10,
                "status": "succeeded",
                "search": "Owned",
            },
        )

    assert response.status_code == 200
    assert response.json()["items"][0] == {
        "id": str(JOB_ID),
        "title": "Owned video",
        "thumbnail_url": "data:image/jpeg;base64,Y292ZXI=",
        "format_name": "1080p MP4",
        "status": "succeeded",
        "progress": 100,
        "error_code": None,
        "created_at": "2026-08-06T10:00:00Z",
        "updated_at": "2026-08-06T10:00:00Z",
        "finished_at": "2026-08-06T10:00:00Z",
        "file_available": False,
        "file_expires_at": None,
    }
    assert response.json()["summary"] == {
        "total": 1,
        "succeeded": 1,
        "active": 0,
        "failed": 0,
    }
    _, kwargs = stubs["history"].calls[0]
    assert kwargs == {
        "page": 2,
        "page_size": 10,
        "status": DownloadStatus.SUCCEEDED,
        "search": "Owned",
    }


def test_provider_status_distinguishes_registered_verified_and_unsupported(
    tmp_path: Path,
) -> None:
    test_client, _ = client(tmp_path)
    with test_client:
        response = test_client.get("/api/providers")

    assert response.status_code == 200
    items = {item["key"]: item for item in response.json()["items"]}
    assert len(items) == 19
    assert items["youtube"]["registered"] is True
    assert items["youtube"]["status"] == "access_required"
    assert items["bilibili"]["status"] == "verified"
    assert items["tiktok"]["status"] == "unknown"
    assert items["wechat_channels"]["status"] == "unsupported"
    assert items["wechat_channels"]["registered"] is False
    assert items["kuaishou"]["registered"] is True
    assert items["kuaishou"]["extractor_exists"] is True
    assert items["kuaishou"]["status"] == "verified"
    assert all(
        sensitive not in response.text.casefold()
        for sensitive in ("credential_version", "egress_affinity", "po_token")
    )


def test_creation_contract_rejects_missing_headers_and_invalid_bodies(
    tmp_path: Path,
) -> None:
    test_client, stubs = client(tmp_path)
    with test_client:
        missing = test_client.post(
            "/api/inspections", json={"url": "https://media.example/video"}
        )
        extra = test_client.post(
            "/api/inspections",
            headers={"Idempotency-Key": "key"},
            json={"url": "https://media.example/video", "cookie": "secret"},
        )
        too_long = test_client.post(
            "/api/inspections",
            headers={"Idempotency-Key": "key"},
            json={"url": "https://example.com/" + "a" * 4_100},
        )
        invalid_uuid = test_client.post(
            "/api/downloads",
            headers={"Idempotency-Key": "key"},
            json={"inspection_id": "bad", "format_id": str(FORMAT_ID)},
        )

    assert {
        missing.status_code,
        extra.status_code,
        too_long.status_code,
        invalid_uuid.status_code,
    } == {422}
    assert stubs["inspect"].calls == []
    assert stubs["create"].calls == []


def test_application_errors_are_rfc9457_problem_details(tmp_path: Path) -> None:
    test_client, stubs = client(tmp_path)
    stubs["get"].error = ApplicationError(ApplicationErrorCode.NOT_FOUND)
    with test_client:
        response = test_client.get(f"/api/downloads/{JOB_ID}")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "not_found"
    assert response.json()["instance"] == f"/api/downloads/{JOB_ID}"


@pytest.mark.parametrize(
    ("code", "status"),
    [
        (ApplicationErrorCode.IDEMPOTENCY_CONFLICT, 409),
        (ApplicationErrorCode.INVALID_URL, 422),
        (ApplicationErrorCode.INSPECTION_FAILED, 502),
        (ApplicationErrorCode.INSPECTION_TIMEOUT, 504),
        (ApplicationErrorCode.PROVIDER_AUTH_REQUIRED, 422),
        (ApplicationErrorCode.PROVIDER_LINK_UNAVAILABLE, 422),
    ],
)
def test_inspection_errors_have_stable_http_mapping(
    tmp_path: Path,
    code: ApplicationErrorCode,
    status: int,
) -> None:
    test_client, stubs = client(tmp_path)
    stubs["inspect"].error = ApplicationError(code)
    with test_client:
        response = test_client.post(
            "/api/inspections",
            headers={"Idempotency-Key": "inspect-1"},
            json={"url": "https://media.example/owned"},
        )

    assert response.status_code == status
    assert response.json()["code"] == code.value
