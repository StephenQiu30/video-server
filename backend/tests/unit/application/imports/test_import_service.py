from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.application.imports import (
    BeginUploadAttemptResult,
    CancelImport,
    CancelImportResult,
    CompletedUploadPart,
    CompleteImportUpload,
    CreateImportResource,
    CreateUploadSession,
    GetImport,
    ImportApplicationError,
    ImportApplicationErrorCode,
    ImportAttemptSnapshot,
    ImportCleanupRef,
    ImportObjectStorageError,
    ImportPersistenceError,
    ImportResourceCreate,
    ImportResourceSaveResult,
    ImportResourceSnapshot,
    MultipartUploadNotFound,
    MultipartUploadRejected,
    UploadLimits,
)
from app.domain.imports import (
    ContentKind,
    ImportErrorCode,
    ImportSourceFormat,
    ImportStatus,
    quarantine_object_key,
)

NOW = datetime(2026, 8, 14, 9, 0, tzinfo=UTC)
RESOURCE_ID = UUID("11111111-1111-4111-8111-111111111111")
OWNER_HASH = "a" * 64
FIVE_MIB = 5 * 1024**2
DECLARED_SIZE = FIVE_MIB + 1
DECLARED_SHA256 = "b" * 64


class FakeFingerprinter:
    def fingerprint(self, namespace: str, *values: str) -> str:
        return "|".join((namespace, *values))


class FakeRepository:
    def __init__(self, resource: ImportResourceSnapshot | None = None) -> None:
        self.resource = resource
        self.created: list[ImportResourceCreate] = []
        self.failed: list[ImportErrorCode] = []
        self.expired = 0
        self.marked_verifying = 0
        self.superseded: tuple[ImportCleanupRef, ...] = ()
        self.fail_error: ImportPersistenceError | None = None

    async def create_resource(
        self, command: ImportResourceCreate, *, now: datetime
    ) -> ImportResourceSaveResult:
        self.created.append(command)
        if self.resource is None:
            self.resource = ImportResourceSnapshot(
                id=command.id,
                owner_hash=command.owner_hash,
                content_kind=command.content_kind.value,
                source_format=command.source_format.value,
                display_name=command.display_name,
                declared_size_bytes=command.declared_size_bytes,
                declared_sha256=command.declared_sha256,
                status=ImportStatus.UPLOADING.value,
                attempt=0,
                error_code=None,
                version=0,
                created_at=now,
                updated_at=now,
                finished_at=None,
            )
        return ImportResourceSaveResult(self.resource, created=True)

    async def get_resource(
        self, resource_id: UUID, owner_hash: str, content_kind: ContentKind
    ) -> ImportResourceSnapshot | None:
        if (
            self.resource is None
            or self.resource.id != resource_id
            or self.resource.owner_hash != owner_hash
            or self.resource.content_kind != content_kind.value
        ):
            return None
        return self.resource

    async def begin_upload_attempt(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        *,
        part_size_bytes: int,
        part_count: int,
        expires_at: datetime,
        now: datetime,
    ) -> BeginUploadAttemptResult:
        assert self.resource is not None
        attempt_number = self.resource.attempt + 1
        attempt = ImportAttemptSnapshot(
            resource_id=resource_id,
            content_kind=content_kind.value,
            attempt=attempt_number,
            status=ImportStatus.UPLOADING.value,
            object_key=quarantine_object_key(content_kind, resource_id, attempt_number),
            upload_id=None,
            content_type=ImportSourceFormat(self.resource.source_format).content_type,
            declared_size_bytes=self.resource.declared_size_bytes,
            part_size_bytes=part_size_bytes,
            part_count=part_count,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        self.resource = replace(
            self.resource,
            attempt=attempt_number,
            active_attempt=attempt,
            updated_at=now,
        )
        return BeginUploadAttemptResult(attempt, self.superseded)

    async def activate_upload_attempt(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        attempt: int,
        *,
        upload_id: str,
        now: datetime,
    ) -> ImportAttemptSnapshot:
        assert self.resource is not None
        assert self.resource.active_attempt is not None
        active = replace(
            self.resource.active_attempt,
            upload_id=upload_id,
            updated_at=now,
        )
        self.resource = replace(self.resource, active_attempt=active, updated_at=now)
        return active

    async def mark_verifying(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        attempt: int,
        *,
        actual_size_bytes: int,
        now: datetime,
    ) -> ImportResourceSnapshot:
        assert self.resource is not None
        assert actual_size_bytes == self.resource.declared_size_bytes
        self.marked_verifying += 1
        self.resource = replace(
            self.resource,
            status=ImportStatus.VERIFYING.value,
            updated_at=now,
            version=self.resource.version + 1,
        )
        return self.resource

    async def fail_attempt(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        attempt: int,
        *,
        error_code: ImportErrorCode,
        now: datetime,
    ) -> ImportResourceSnapshot:
        assert self.resource is not None
        if self.fail_error is not None:
            raise self.fail_error
        self.failed.append(error_code)
        retryable = error_code.retryable
        self.resource = replace(
            self.resource,
            status=(
                ImportStatus.UPLOADING.value if retryable else ImportStatus.FAILED.value
            ),
            error_code=error_code.value,
            updated_at=now,
            finished_at=None if retryable else now,
        )
        return self.resource

    async def expire_attempt(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        attempt: int,
        *,
        now: datetime,
    ) -> ImportResourceSnapshot:
        assert self.resource is not None
        self.expired += 1
        self.resource = replace(
            self.resource,
            status=ImportStatus.UPLOADING.value,
            error_code=ImportErrorCode.UPLOAD_SESSION_EXPIRED.value,
            updated_at=now,
            finished_at=None,
        )
        return self.resource

    async def cancel_resource(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        *,
        now: datetime,
    ) -> CancelImportResult:
        if self.resource is None:
            raise AssertionError("resource is missing")
        cleanup = ()
        if self.resource.active_attempt is not None:
            active = self.resource.active_attempt
            cleanup = (ImportCleanupRef(active.object_key, active.upload_id),)
        self.resource = replace(
            self.resource,
            status=ImportStatus.CANCELLED.value,
            updated_at=now,
            finished_at=now,
        )
        return CancelImportResult(self.resource, cleanup)


class FakeHead:
    def __init__(self, size_bytes: int, content_type: str = "video/mp4") -> None:
        self.size_bytes = size_bytes
        self.sha256: str | None = None
        self.content_type: str | None = content_type


class FakeStorage:
    def __init__(self) -> None:
        self.created: list[tuple[str, str, str | None]] = []
        self.signed: list[int] = []
        self.local_browser_signing: list[bool] = []
        self.completed: list[tuple[CompletedUploadPart, ...]] = []
        self.aborted: list[tuple[str, str]] = []
        self.deleted: list[str] = []
        self.head: FakeHead | None = FakeHead(DECLARED_SIZE)
        self.create_error: Exception | None = None
        self.complete_error: Exception | None = None
        self.stat_error: Exception | None = None
        self.cleanup_error = False

    async def create_multipart_upload(
        self,
        object_key: str,
        *,
        content_type: str,
        declared_sha256: str | None = None,
    ) -> str:
        if self.create_error is not None:
            raise self.create_error
        self.created.append((object_key, content_type, declared_sha256))
        return "upload-1"

    async def presign_upload_part(
        self,
        object_key: str,
        upload_id: str,
        part_number: int,
        *,
        ttl_seconds: int,
        use_local_browser_endpoint: bool = False,
    ) -> str:
        assert object_key.startswith("quarantine/")
        assert upload_id == "upload-1"
        assert 0 < ttl_seconds <= 900
        self.signed.append(part_number)
        self.local_browser_signing.append(use_local_browser_endpoint)
        return f"https://objects.example/part/{part_number}"

    async def complete_multipart_upload(
        self,
        object_key: str,
        upload_id: str,
        parts: tuple[CompletedUploadPart, ...],
    ) -> str | None:
        if self.complete_error is not None:
            raise self.complete_error
        self.completed.append(parts)
        return "etag"

    async def abort_multipart_upload(self, object_key: str, upload_id: str) -> None:
        if self.cleanup_error:
            raise ImportObjectStorageError("abort failed")
        self.aborted.append((object_key, upload_id))

    async def stat(self, object_key: str) -> FakeHead | None:
        if self.stat_error is not None:
            raise self.stat_error
        return self.head

    async def delete(self, object_key: str) -> None:
        if self.cleanup_error:
            raise ImportObjectStorageError("delete failed")
        self.deleted.append(object_key)


def resource(
    *,
    status: ImportStatus = ImportStatus.UPLOADING,
    active_attempt: ImportAttemptSnapshot | None = None,
) -> ImportResourceSnapshot:
    return ImportResourceSnapshot(
        id=RESOURCE_ID,
        owner_hash=OWNER_HASH,
        content_kind=ContentKind.VIDEO.value,
        source_format=ImportSourceFormat.MP4.value,
        display_name="example.mp4",
        declared_size_bytes=DECLARED_SIZE,
        declared_sha256=DECLARED_SHA256,
        status=status.value,
        attempt=0 if active_attempt is None else active_attempt.attempt,
        error_code=None,
        version=0,
        created_at=NOW,
        updated_at=NOW,
        finished_at=None,
        active_attempt=active_attempt,
    )


def attempt(*, expired: bool = False) -> ImportAttemptSnapshot:
    return ImportAttemptSnapshot(
        resource_id=RESOURCE_ID,
        content_kind=ContentKind.VIDEO.value,
        attempt=1,
        status=ImportStatus.UPLOADING.value,
        object_key=quarantine_object_key(ContentKind.VIDEO, RESOURCE_ID, 1),
        upload_id="upload-1",
        content_type="video/mp4",
        declared_size_bytes=DECLARED_SIZE,
        part_size_bytes=FIVE_MIB,
        part_count=2,
        expires_at=NOW - timedelta(seconds=1)
        if expired
        else NOW + timedelta(minutes=15),
        created_at=NOW,
        updated_at=NOW,
    )


def limits() -> UploadLimits:
    return UploadLimits(
        part_size_bytes=FIVE_MIB,
        max_parts=1000,
        max_concurrency=4,
        session_ttl=timedelta(minutes=15),
    )


def completed_parts() -> tuple[CompletedUploadPart, ...]:
    return (
        CompletedUploadPart(2, '"22222222222222222222222222222222"'),
        CompletedUploadPart(1, "11111111111111111111111111111111"),
    )


async def test_create_resource_derives_safe_server_contract() -> None:
    repository = FakeRepository()
    use_case = CreateImportResource(
        repository=repository,
        fingerprinter=FakeFingerprinter(),
        now=lambda: NOW,
        new_id=lambda: RESOURCE_ID,
        media_enabled=True,
        document_enabled=True,
        media_max_bytes=2 * 1024**3,
        document_max_bytes=50 * 1024**2,
        rights_statement_version="content-rights-v1",
    )

    view = await use_case(
        owner_hash=OWNER_HASH,
        idempotency_key="request-1",
        content_kind=ContentKind.VIDEO,
        source_format=ImportSourceFormat.MP4,
        file_name=" C:\\private\\example.mp4 ",
        declared_size_bytes=DECLARED_SIZE,
        declared_sha256=DECLARED_SHA256,
        rights_accepted=True,
    )

    command = repository.created[0]
    assert view.status is ImportStatus.UPLOADING
    assert command.display_name == "example.mp4"
    assert command.content_type == "video/mp4"
    assert command.rights_statement_version == "content-rights-v1"
    assert command.request_fingerprint.startswith("content-import|video|mp4|")


async def test_create_resource_accepts_only_supported_screenplay_format() -> None:
    repository = FakeRepository()
    use_case = CreateImportResource(
        repository=repository,
        fingerprinter=FakeFingerprinter(),
        now=lambda: NOW,
        new_id=lambda: RESOURCE_ID,
        media_enabled=False,
        document_enabled=True,
        media_max_bytes=2 * 1024**3,
        document_max_bytes=50 * 1024**2,
        rights_statement_version="content-rights-v1",
    )

    view = await use_case(
        owner_hash=OWNER_HASH,
        idempotency_key="request-1",
        content_kind=ContentKind.SCREENPLAY,
        source_format=ImportSourceFormat.DOCX,
        file_name="剧本.docx",
        declared_size_bytes=1024,
        declared_sha256=DECLARED_SHA256,
        rights_accepted=True,
    )

    assert view.content_kind is ContentKind.SCREENPLAY
    assert view.source_format is ImportSourceFormat.DOCX
    assert repository.created[0].content_type.endswith("wordprocessingml.document")


@pytest.mark.parametrize(
    "overrides",
    (
        {"rights_accepted": False},
        {"source_format": ImportSourceFormat.PDF},
        {"declared_size_bytes": 0},
        {"declared_sha256": "invalid"},
        {"file_name": "example.pdf"},
    ),
)
async def test_create_resource_rejects_untrusted_invalid_declarations(
    overrides: dict[str, object],
) -> None:
    use_case = CreateImportResource(
        repository=FakeRepository(),
        fingerprinter=FakeFingerprinter(),
        now=lambda: NOW,
        new_id=lambda: RESOURCE_ID,
        media_enabled=True,
        document_enabled=True,
        media_max_bytes=2 * 1024**3,
        document_max_bytes=50 * 1024**2,
        rights_statement_version="content-rights-v1",
    )
    values: dict[str, object] = {
        "owner_hash": OWNER_HASH,
        "idempotency_key": "request-1",
        "content_kind": ContentKind.VIDEO,
        "source_format": ImportSourceFormat.MP4,
        "file_name": "example.mp4",
        "declared_size_bytes": DECLARED_SIZE,
        "declared_sha256": DECLARED_SHA256,
        "rights_accepted": True,
    }
    values.update(overrides)

    with pytest.raises(ImportApplicationError) as captured:
        await use_case(**values)  # type: ignore[arg-type]

    assert captured.value.code is ImportApplicationErrorCode.INVALID_REQUEST


async def test_create_resource_is_fail_closed_when_feature_disabled() -> None:
    use_case = CreateImportResource(
        repository=FakeRepository(),
        fingerprinter=FakeFingerprinter(),
        now=lambda: NOW,
        new_id=lambda: RESOURCE_ID,
        media_enabled=False,
        document_enabled=False,
        media_max_bytes=2 * 1024**3,
        document_max_bytes=50 * 1024**2,
        rights_statement_version="content-rights-v1",
    )

    with pytest.raises(ImportApplicationError) as captured:
        await use_case(
            owner_hash=OWNER_HASH,
            idempotency_key="request-1",
            content_kind=ContentKind.VIDEO,
            source_format=ImportSourceFormat.MP4,
            file_name="example.mp4",
            declared_size_bytes=DECLARED_SIZE,
            declared_sha256=DECLARED_SHA256,
            rights_accepted=True,
        )

    assert captured.value.code is ImportApplicationErrorCode.DISABLED


async def test_upload_session_uses_deterministic_key_and_bounded_parts() -> None:
    repository = FakeRepository(resource())
    storage = FakeStorage()
    use_case = CreateUploadSession(
        repository, storage, now=lambda: NOW, limits=limits()
    )

    session = await use_case(RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO)

    expected_key = quarantine_object_key(ContentKind.VIDEO, RESOURCE_ID, 1)
    assert storage.created == [(expected_key, "video/mp4", DECLARED_SHA256)]
    assert storage.signed == [1, 2]
    assert session.part_size_bytes == FIVE_MIB
    assert session.part_count == 2
    assert session.max_concurrency == 4
    assert tuple(part.part_number for part in session.parts) == (1, 2)
    assert "https://objects.example" not in repr(session)
    assert DECLARED_SHA256 not in repr(repository.resource)
    assert "example.mp4" not in repr(repository.resource)


async def test_upload_session_can_sign_for_the_local_web_endpoint() -> None:
    repository = FakeRepository(resource())
    storage = FakeStorage()

    await CreateUploadSession(repository, storage, now=lambda: NOW, limits=limits())(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        use_local_browser_endpoint=True,
    )

    assert storage.local_browser_signing == [True, True]


async def test_upload_session_cleans_superseded_attempt() -> None:
    repository = FakeRepository(replace(resource(), attempt=1))
    stale = ImportCleanupRef(
        quarantine_object_key(ContentKind.VIDEO, RESOURCE_ID, 1), "stale-upload"
    )
    repository.superseded = (stale,)
    storage = FakeStorage()

    await CreateUploadSession(repository, storage, now=lambda: NOW, limits=limits())(
        RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO
    )

    assert storage.aborted[0] == (stale.object_key, "stale-upload")
    assert storage.deleted[0] == stale.object_key


async def test_upload_session_rejects_out_of_scope_cleanup_key() -> None:
    repository = FakeRepository(resource())
    repository.superseded = (
        ImportCleanupRef("downloads/another-owner/video.mp4", "stale-upload"),
    )
    storage = FakeStorage()

    with pytest.raises(ImportApplicationError) as captured:
        await CreateUploadSession(
            repository, storage, now=lambda: NOW, limits=limits()
        )(RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO)

    assert captured.value.code is ImportApplicationErrorCode.INTERNAL_ERROR
    assert storage.aborted == []
    assert storage.deleted == []


async def test_upload_session_storage_failure_has_stable_error() -> None:
    repository = FakeRepository(resource())
    storage = FakeStorage()
    storage.create_error = ImportObjectStorageError("unavailable")

    with pytest.raises(ImportApplicationError) as captured:
        await CreateUploadSession(
            repository, storage, now=lambda: NOW, limits=limits()
        )(RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO)

    assert captured.value.code is ImportApplicationErrorCode.STORAGE_UNAVAILABLE
    assert repository.failed == [ImportErrorCode.STORAGE_UNAVAILABLE]


async def test_complete_upload_heads_object_and_atomically_requests_verify() -> None:
    current_attempt = attempt()
    repository = FakeRepository(resource(active_attempt=current_attempt))
    storage = FakeStorage()

    view = await CompleteImportUpload(repository, storage, now=lambda: NOW)(
        RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO, completed_parts()
    )

    assert view.status is ImportStatus.VERIFYING
    assert repository.marked_verifying == 1
    assert storage.completed == [completed_parts()]
    assert storage.deleted == []


async def test_duplicate_complete_recovers_from_existing_object() -> None:
    repository = FakeRepository(resource(active_attempt=attempt()))
    storage = FakeStorage()
    storage.complete_error = MultipartUploadNotFound("already completed")

    view = await CompleteImportUpload(repository, storage, now=lambda: NOW)(
        RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO, completed_parts()
    )

    assert view.status is ImportStatus.VERIFYING
    assert repository.marked_verifying == 1


async def test_duplicate_complete_maps_head_failure_to_storage_error() -> None:
    repository = FakeRepository(resource(active_attempt=attempt()))
    storage = FakeStorage()
    storage.complete_error = MultipartUploadNotFound("already completed")
    storage.stat_error = ImportObjectStorageError("HEAD unavailable")

    with pytest.raises(ImportApplicationError) as captured:
        await CompleteImportUpload(repository, storage, now=lambda: NOW)(
            RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO, completed_parts()
        )

    assert captured.value.code is ImportApplicationErrorCode.STORAGE_UNAVAILABLE
    assert repository.failed == []


async def test_complete_rejects_invalid_part_manifest_without_touching_storage() -> (
    None
):
    repository = FakeRepository(resource(active_attempt=attempt()))
    storage = FakeStorage()

    with pytest.raises(ImportApplicationError) as captured:
        await CompleteImportUpload(repository, storage, now=lambda: NOW)(
            RESOURCE_ID,
            OWNER_HASH,
            ContentKind.VIDEO,
            (CompletedUploadPart(1, "1" * 32),),
        )

    assert captured.value.code is ImportApplicationErrorCode.UPLOAD_INCOMPLETE
    assert storage.completed == []


async def test_complete_rejected_by_storage_fails_and_cleans_attempt() -> None:
    current_attempt = attempt()
    repository = FakeRepository(resource(active_attempt=current_attempt))
    storage = FakeStorage()
    storage.complete_error = MultipartUploadRejected("missing part")

    with pytest.raises(ImportApplicationError) as captured:
        await CompleteImportUpload(repository, storage, now=lambda: NOW)(
            RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO, completed_parts()
        )

    assert captured.value.code is ImportApplicationErrorCode.UPLOAD_INCOMPLETE
    assert repository.failed == [ImportErrorCode.UPLOAD_INCOMPLETE]
    assert storage.aborted == [(current_attempt.object_key, "upload-1")]
    assert storage.deleted == [current_attempt.object_key]


async def test_complete_size_mismatch_fails_and_cleans_object() -> None:
    current_attempt = attempt()
    repository = FakeRepository(resource(active_attempt=current_attempt))
    storage = FakeStorage()
    storage.head = FakeHead(DECLARED_SIZE - 1)

    with pytest.raises(ImportApplicationError) as captured:
        await CompleteImportUpload(repository, storage, now=lambda: NOW)(
            RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO, completed_parts()
        )

    assert captured.value.code is ImportApplicationErrorCode.SIZE_MISMATCH
    assert repository.failed == [ImportErrorCode.SIZE_MISMATCH]
    assert storage.deleted == [current_attempt.object_key]


async def test_complete_keeps_object_when_failure_state_does_not_commit() -> None:
    current_attempt = attempt()
    repository = FakeRepository(resource(active_attempt=current_attempt))
    repository.fail_error = ImportPersistenceError("database unavailable")
    storage = FakeStorage()
    storage.head = FakeHead(DECLARED_SIZE - 1)

    with pytest.raises(ImportApplicationError) as captured:
        await CompleteImportUpload(repository, storage, now=lambda: NOW)(
            RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO, completed_parts()
        )

    assert captured.value.code is ImportApplicationErrorCode.INTERNAL_ERROR
    assert storage.aborted == []
    assert storage.deleted == []


async def test_expired_complete_marks_state_and_cleans_multipart() -> None:
    current_attempt = attempt(expired=True)
    repository = FakeRepository(resource(active_attempt=current_attempt))
    storage = FakeStorage()

    with pytest.raises(ImportApplicationError) as captured:
        await CompleteImportUpload(repository, storage, now=lambda: NOW)(
            RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO, completed_parts()
        )

    assert captured.value.code is ImportApplicationErrorCode.UPLOAD_SESSION_EXPIRED
    assert repository.expired == 1
    assert storage.aborted == [(current_attempt.object_key, "upload-1")]

    refreshed = await CreateUploadSession(
        repository, storage, now=lambda: NOW, limits=limits()
    )(RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO)
    assert refreshed.attempt == 2


async def test_cancel_is_durable_when_object_cleanup_is_unavailable() -> None:
    repository = FakeRepository(resource(active_attempt=attempt()))
    storage = FakeStorage()
    storage.cleanup_error = True

    view = await CancelImport(repository, storage, now=lambda: NOW)(
        RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO
    )

    assert view.status is ImportStatus.CANCELLED
    assert repository.resource is not None
    assert repository.resource.status == ImportStatus.CANCELLED.value


async def test_get_import_does_not_reveal_another_owner_resource() -> None:
    repository = FakeRepository(resource())
    storage = FakeStorage()

    with pytest.raises(ImportApplicationError) as captured:
        await GetImport(repository, storage, now=lambda: NOW)(
            RESOURCE_ID, "c" * 64, ContentKind.VIDEO
        )

    assert captured.value.code is ImportApplicationErrorCode.NOT_FOUND


async def test_get_import_expires_and_cleans_an_abandoned_upload() -> None:
    current_attempt = attempt(expired=True)
    repository = FakeRepository(resource(active_attempt=current_attempt))
    storage = FakeStorage()

    view = await GetImport(repository, storage, now=lambda: NOW)(
        RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO
    )

    assert view.status is ImportStatus.UPLOADING
    assert view.error_code is ImportErrorCode.UPLOAD_SESSION_EXPIRED
    assert repository.expired == 1
    assert storage.aborted == [(current_attempt.object_key, "upload-1")]
    assert storage.deleted == [current_attempt.object_key]


def test_upload_limits_enforce_multipart_budget() -> None:
    policy = limits()

    assert policy.part_count(DECLARED_SIZE) == 2
    with pytest.raises(ValueError, match="multipart budget"):
        policy.part_count(FIVE_MIB * 1000 + 1)
