from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from app.application.import_execution import (
    ImportExecution,
    ImportExecutionSettings,
    ImportRecoverySweeper,
    ImportVerificationClaim,
    ImportVerificationRejected,
    ImportWorkspace,
    VerifiedImportArtifact,
)
from app.application.imports import ImportDisposition
from app.domain.imports import (
    ContentKind,
    ImportErrorCode,
    ImportSourceFormat,
)

NOW = datetime(2026, 8, 14, 10, 0, tzinfo=UTC)
RESOURCE_ID = UUID("11111111-1111-4111-8111-111111111111")


@dataclass(frozen=True)
class StoredObjectView:
    object_key: str
    last_modified: datetime


def claim() -> ImportVerificationClaim:
    return ImportVerificationClaim(
        resource_id=RESOURCE_ID,
        content_kind=ContentKind.VIDEO,
        source_format=ImportSourceFormat.MP4,
        attempt=2,
        version=4,
        object_key=f"quarantine/video/{RESOURCE_ID}/2/source.mp4",
        declared_size_bytes=128,
        declared_sha256="a" * 64,
    )


def artifact() -> VerifiedImportArtifact:
    return VerifiedImportArtifact(
        sha256="a" * 64,
        size_bytes=128,
        duration_ms=5000,
        container="mp4",
        content_type="video/mp4",
        media_metadata={"video_streams": 1, "audio_streams": 0},
    )


class FakeRepository:
    def __init__(self) -> None:
        self.claimed: ImportVerificationClaim | None = claim()
        self.heartbeats: list[tuple[str, int]] = []
        self.owned = True
        self.completed: list[tuple[object, ...]] = []
        self.failed: list[tuple[ImportErrorCode, str]] = []
        self.complete_error: Exception | None = None
        self.recovered: tuple[UUID, ...] = ()
        self.expected_keys: frozenset[str] = frozenset()

    async def claim_verification(self, *args, **kwargs):
        return self.claimed

    async def heartbeat_verification(self, *args, **kwargs):
        self.heartbeats.append((kwargs["stage"], kwargs["progress"]))
        return self.owned

    async def complete_verification(self, *args, **kwargs):
        if self.complete_error is not None:
            raise self.complete_error
        self.completed.append((*args, kwargs))

    async def fail_verification(self, claim, error_code, **kwargs):
        self.failed.append((error_code, kwargs["worker_id"]))

    async def recover_expired_verifications(self, now, *, limit):
        return self.recovered

    async def expected_artifact_object_keys(self):
        return self.expected_keys


class FakeStorage:
    def __init__(self) -> None:
        self.downloads: list[tuple[str, Path]] = []
        self.promotions: list[tuple[str, str]] = []
        self.deletes: list[str] = []
        self.objects: tuple[StoredObjectView, ...] = ()

    async def download(self, object_key: str, target: Path) -> None:
        self.downloads.append((object_key, target))
        target.write_bytes(b"downloaded")

    async def promote(self, source_key: str, destination_key: str, **kwargs):
        self.promotions.append((source_key, destination_key))
        return object()

    async def delete(self, object_key: str) -> None:
        self.deletes.append(object_key)

    async def list(self, prefix: str):
        assert prefix == "downloads/"
        return self.objects


class FakeWorkspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.cleaned: list[tuple[str, Path | None]] = []
        self.orphan_cleanups: list[tuple[datetime, timedelta, int]] = []

    async def create(self, task_id: str) -> ImportWorkspace:
        path = self.root / f"{task_id}-random"
        path.mkdir()
        return ImportWorkspace(path, path / "video.mp4")

    async def cleanup(self, task_id: str, workspace: Path | None) -> None:
        self.cleaned.append((task_id, workspace))

    async def cleanup_orphans(self, now, *, older_than, limit):
        self.orphan_cleanups.append((now, older_than, limit))
        return 0


class FakeVerifier:
    def __init__(self) -> None:
        self.error: Exception | None = None
        self.paths: list[Path] = []

    async def __call__(self, path: Path, requested: ImportVerificationClaim):
        self.paths.append(path)
        if self.error is not None:
            raise self.error
        return artifact()


def execution(tmp_path: Path):
    repository = FakeRepository()
    storage = FakeStorage()
    workspace = FakeWorkspace(tmp_path)
    verifier = FakeVerifier()
    service = ImportExecution(
        repository=repository,
        storage=storage,
        workspace=workspace,
        video_verifier=verifier,
        clock=lambda: NOW,
        settings=ImportExecutionSettings(
            worker_id="import-worker-a",
            bucket="video-artifacts",
            workspace_root=tmp_path,
            lease_for=timedelta(seconds=30),
            heartbeat_interval=5,
        ),
    )
    return service, repository, storage, workspace, verifier


async def test_success_promotes_to_deterministic_artifact_then_commits_and_cleans(
    tmp_path: Path,
) -> None:
    service, repository, storage, workspace, verifier = execution(tmp_path)

    disposition = await service.execute(RESOURCE_ID, ContentKind.VIDEO, 2, 4)

    assert disposition is ImportDisposition.ACK
    assert repository.heartbeats == [
        ("verifying", 60),
        ("verifying", 75),
        ("uploading", 95),
    ]
    assert storage.promotions == [
        (
            claim().object_key,
            f"downloads/{RESOURCE_ID}/2/video.mp4",
        )
    ]
    assert len(repository.completed) == 1
    assert storage.deletes == [claim().object_key]
    assert len(verifier.paths) == len(workspace.cleaned) == 1


async def test_validation_rejection_is_terminal_and_cleans_quarantine(
    tmp_path: Path,
) -> None:
    service, repository, storage, _, verifier = execution(tmp_path)
    verifier.error = ImportVerificationRejected(
        ImportErrorCode.SHA256_MISMATCH, "mismatch"
    )

    disposition = await service.execute(RESOURCE_ID, ContentKind.VIDEO, 2, 4)

    assert disposition is ImportDisposition.ACK
    assert repository.failed == [(ImportErrorCode.SHA256_MISMATCH, "import-worker-a")]
    assert repository.completed == []
    assert storage.promotions == []
    assert storage.deletes == [claim().object_key]


async def test_database_failure_after_promotion_retries_without_deleting_recovery_copy(
    tmp_path: Path,
) -> None:
    service, repository, storage, workspace, _ = execution(tmp_path)
    repository.complete_error = RuntimeError("database unavailable")

    disposition = await service.execute(RESOURCE_ID, ContentKind.VIDEO, 2, 4)

    assert disposition is ImportDisposition.RETRY
    assert len(storage.promotions) == 1
    assert storage.deletes == []
    assert len(workspace.cleaned) == 1


async def test_lost_lease_converges_without_touching_storage(tmp_path: Path) -> None:
    service, repository, storage, _, _ = execution(tmp_path)
    repository.owned = False

    disposition = await service.execute(RESOURCE_ID, ContentKind.VIDEO, 2, 4)

    assert disposition is ImportDisposition.ACK
    assert storage.downloads == []
    assert storage.promotions == []
    assert storage.deletes == []


async def test_stale_message_acks_and_unimplemented_document_routes_to_dlq(
    tmp_path: Path,
) -> None:
    service, repository, storage, _, _ = execution(tmp_path)
    repository.claimed = None

    stale = await service.execute(RESOURCE_ID, ContentKind.VIDEO, 2, 3)
    document = await service.execute(RESOURCE_ID, ContentKind.SCREENPLAY, 1, 1)

    assert stale is ImportDisposition.ACK
    assert document is ImportDisposition.RETRY
    assert storage.downloads == []


async def test_recovery_sweeper_requeues_leases_and_only_deletes_safe_old_orphans(
    tmp_path: Path,
) -> None:
    _, repository, storage, workspace, _ = execution(tmp_path)
    repository.recovered = (RESOURCE_ID,)
    expected = f"downloads/{RESOURCE_ID}/2/video.mp4"
    repository.expected_keys = frozenset({expected})
    orphan = "downloads/22222222-2222-4222-8222-222222222222/1/video.mp4"
    fresh = "downloads/33333333-3333-4333-8333-333333333333/1/video.mp4"
    storage.objects = (
        StoredObjectView(expected, NOW - timedelta(hours=2)),
        StoredObjectView(orphan, NOW - timedelta(hours=2)),
        StoredObjectView(fresh, NOW),
        StoredObjectView("downloads/unmanaged.bin", NOW - timedelta(days=1)),
    )
    sweeper = ImportRecoverySweeper(
        repository,
        storage,
        workspace,
        lambda: NOW,
        interval=5,
        batch_size=10,
        workspace_grace=timedelta(minutes=30),
        artifact_orphan_grace=timedelta(hours=1),
        delete_timeout=5,
    )

    recovered = await sweeper.tick()

    assert recovered == (RESOURCE_ID,)
    assert storage.deletes == [orphan]
    assert workspace.orphan_cleanups == [(NOW, timedelta(minutes=30), 10)]
