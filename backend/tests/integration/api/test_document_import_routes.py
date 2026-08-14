from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import DocumentImportUseCases
from app.application.auth import CurrentUser, UserRole
from app.application.documents import DocumentPage, DocumentView
from app.application.imports import (
    ImportView,
    UploadPartTarget,
    UploadSessionView,
)
from app.core.config import Settings
from app.domain.imports import ContentKind, ImportSourceFormat, ImportStatus
from app.main import create_app
from fastapi.testclient import TestClient

NOW = datetime(2026, 8, 14, 14, 0, tzinfo=UTC)
DOCUMENT_ID = UUID("55555555-5555-4555-8555-555555555555")
TEST_USER = CurrentUser(
    id=DOCUMENT_ID,
    username="screenwriter",
    email="writer@example.com",
    role=UserRole.USER,
    created_at=NOW,
    updated_at=NOW,
)


class StubUseCase:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def __call__(self, *args: object, **kwargs: object) -> object:
        self.calls.append((args, kwargs))
        return self.result


def document_view(status: ImportStatus = ImportStatus.UPLOADING) -> ImportView:
    return ImportView(
        id=DOCUMENT_ID,
        content_kind=ContentKind.SCREENPLAY,
        source_format=ImportSourceFormat.FOUNTAIN,
        display_name="owned.fountain",
        declared_size_bytes=2048,
        status=status,
        attempt=1,
        error_code=None,
        version=2,
        created_at=NOW,
        updated_at=NOW,
        finished_at=None,
    )


def session_view() -> UploadSessionView:
    return UploadSessionView(
        resource_id=DOCUMENT_ID,
        attempt=1,
        part_size_bytes=5 * 1024**2,
        part_count=1,
        max_concurrency=4,
        expires_at=NOW + timedelta(minutes=15),
        parts=(UploadPartTarget(1, "https://objects.example/part?private=1"),),
    )


def detail_view() -> DocumentView:
    return DocumentView(
        id=DOCUMENT_ID,
        title="owned",
        original_filename="owned.fountain",
        source_format=ImportSourceFormat.FOUNTAIN,
        declared_size_bytes=2048,
        status=ImportStatus.UPLOADING,
        attempt=1,
        error_code=None,
        version=2,
        detected_language=None,
        scene_count=None,
        character_count=None,
        quality_warnings=(),
        expires_at=None,
        created_at=NOW,
        updated_at=NOW,
        finished_at=None,
        preview="<script>plain text only</script>",
        preview_truncated=True,
    )


def client(tmp_path: Path) -> tuple[TestClient, dict[str, StubUseCase]]:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    stubs = {
        "create": StubUseCase(document_view()),
        "session": StubUseCase(session_view()),
        "complete": StubUseCase(document_view(ImportStatus.VERIFYING)),
        "get": StubUseCase(document_view()),
        "detail": StubUseCase(detail_view()),
        "list": StubUseCase(DocumentPage((detail_view(),), 1, 20, 1)),
        "delete": StubUseCase(None),
        "cancel": StubUseCase(document_view(ImportStatus.CANCELLED)),
    }
    app.state.document_import_use_cases = DocumentImportUseCases(
        create_resource=stubs["create"],  # type: ignore[arg-type]
        create_upload_session=stubs["session"],  # type: ignore[arg-type]
        complete_upload=stubs["complete"],  # type: ignore[arg-type]
        get_import=stubs["get"],  # type: ignore[arg-type]
        cancel_import=stubs["cancel"],  # type: ignore[arg-type]
        get_document=stubs["detail"],  # type: ignore[arg-type]
        list_documents=stubs["list"],  # type: ignore[arg-type]
        delete_document=stubs["delete"],  # type: ignore[arg-type]
    )
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    return TestClient(app), stubs


def body() -> dict[str, object]:
    return {
        "file_name": "owned.fountain",
        "source_format": "fountain",
        "declared_size_bytes": 2048,
        "declared_sha256": "b" * 64,
        "rights_accepted": True,
    }


def test_document_use_cases_are_required(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/documents", headers={"Idempotency-Key": "document-1"}, json=body()
        )
    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


def test_document_routes_delegate_owner_and_hide_storage(tmp_path: Path) -> None:
    test_client, stubs = client(tmp_path)
    with test_client:
        created = test_client.post(
            "/api/documents", headers={"Idempotency-Key": "document-1"}, json=body()
        )
        fetched = test_client.get(f"/api/documents/{DOCUMENT_ID}")
        listed = test_client.get("/api/documents")
        session = test_client.post(f"/api/documents/{DOCUMENT_ID}/upload-sessions")
        completed = test_client.post(
            f"/api/documents/{DOCUMENT_ID}/complete",
            json={"parts": [{"part_number": 1, "etag": "1" * 32}]},
        )
        cancelled = test_client.post(f"/api/documents/{DOCUMENT_ID}/cancel")
        deleted = test_client.delete(f"/api/documents/{DOCUMENT_ID}")

    assert created.status_code == session.status_code == 201
    assert fetched.status_code == listed.status_code == completed.status_code == 200
    assert cancelled.status_code == 200
    assert deleted.status_code == 204 and deleted.content == b""
    assert created.headers["location"] == f"/api/documents/{DOCUMENT_ID}"
    assert created.json()["source_format"] == "fountain"
    assert fetched.json()["title"] == "owned"
    assert fetched.json()["preview"] == "<script>plain text only</script>"
    assert fetched.json()["preview_truncated"] is True
    assert listed.json()["total"] == 1
    assert completed.json()["status"] == "verifying"
    assert cancelled.json()["status"] == "cancelled"
    assert "object_key" not in session.text and "upload_id" not in session.text
    assert "object_key" not in fetched.text and "text_sha256" not in fetched.text
    create = stubs["create"].calls[0][1]
    assert create["owner_hash"] == TEST_USER.owner_hash
    assert create["content_kind"] is ContentKind.SCREENPLAY
    assert create["source_format"] is ImportSourceFormat.FOUNTAIN
    complete = stubs["complete"].calls[0][0]
    assert complete[:3] == (DOCUMENT_ID, TEST_USER.owner_hash, ContentKind.SCREENPLAY)
    assert stubs["delete"].calls[0][0] == (DOCUMENT_ID, TEST_USER.owner_hash)


def test_document_request_is_strict_and_format_bounded(tmp_path: Path) -> None:
    test_client, stubs = client(tmp_path)
    with test_client:
        storage_control = test_client.post(
            "/api/documents",
            headers={"Idempotency-Key": "document-1"},
            json=body() | {"object_key": "documents/foreign"},
        )
        video = test_client.post(
            "/api/documents",
            headers={"Idempotency-Key": "document-2"},
            json=body() | {"source_format": "mp4"},
        )
    assert storage_control.status_code == video.status_code == 422
    assert stubs["create"].calls == []
