from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.api.auth_dependencies import get_current_admin, get_current_user
from app.application.auth import CurrentUser, UserRole
from app.application.storage_files import (
    StorageCleanupResult,
    StoredFilePage,
    StoredFileView,
)
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

NOW = datetime(2026, 8, 18, 12, tzinfo=UTC)
LONG_FILE_NAME = "超长视频标题" * 30
ADMIN = CurrentUser(
    id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    username="admin_user",
    email="admin@example.com",
    role=UserRole.ADMIN,
    created_at=NOW,
    updated_at=NOW,
)
USER = CurrentUser(
    id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
    username="normal_user",
    email="user@example.com",
    role=UserRole.USER,
    created_at=NOW,
    updated_at=NOW,
)


class StorageFilesStub:
    def __init__(self) -> None:
        self.list_calls: list[tuple[int, int]] = []
        self.cleanup_calls: list[int] = []

    async def list_files(self, *, page: int, page_size: int) -> StoredFilePage:
        self.list_calls.append((page, page_size))
        return StoredFilePage(
            items=(
                StoredFileView(
                    id=UUID("11111111-1111-4111-8111-111111111111"),
                    category="video",
                    name=LONG_FILE_NAME,
                    object_count=1,
                    size_bytes=1024,
                    created_at=NOW,
                ),
            ),
            page=page,
            page_size=page_size,
            total=21,
        )

    async def cleanup(self, *, older_than_days: int) -> StorageCleanupResult:
        self.cleanup_calls.append(older_than_days)
        return StorageCleanupResult(older_than_days, 2, 3, 4096, 0)


def _app(tmp_path: Path, stub: StorageFilesStub):
    app = create_app(Settings(app_env="test"))
    app.state.storage_file_service = stub
    return app


def test_admin_files_are_paginated_and_cleanup_defaults_to_thirty_days(
    tmp_path: Path,
) -> None:
    stub = StorageFilesStub()
    app = _app(tmp_path, stub)
    app.dependency_overrides[get_current_admin] = lambda: ADMIN

    with TestClient(app) as client:
        listing = client.get("/api/admin/files", params={"page": 2, "page_size": 10})
        cleanup = client.post("/api/admin/files/cleanup", json={})

    assert listing.status_code == 200
    assert listing.json()["total"] == 21
    assert listing.json()["items"][0]["name"] == LONG_FILE_NAME
    assert "object_key" not in listing.text
    assert stub.list_calls == [(2, 10)]
    assert cleanup.status_code == 200
    assert cleanup.json() == {
        "older_than_days": 30,
        "removed_resources": 2,
        "removed_objects": 3,
        "freed_bytes": 4096,
        "failed_resources": 0,
    }
    assert stub.cleanup_calls == [30]


def test_admin_files_reject_non_admin(tmp_path: Path) -> None:
    stub = StorageFilesStub()
    app = _app(tmp_path, stub)
    app.dependency_overrides[get_current_user] = lambda: USER

    with TestClient(app) as client:
        listing = client.get("/api/admin/files")
        cleanup = client.post("/api/admin/files/cleanup", json={"older_than_days": 30})

    assert listing.status_code == cleanup.status_code == 403
    assert stub.list_calls == []
    assert stub.cleanup_calls == []
