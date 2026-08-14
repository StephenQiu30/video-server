from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.application.imports import (
    ImportObjectStorageError,
    MultipartUploadNotFound,
    MultipartUploadRejected,
)
from app.core.config import Settings
from app.infrastructure.object_storage import MinioObjectStorage, MultipartUploadPart
from minio.commonconfig import CopySource
from pydantic import SecretStr


class FakeMinio:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def bucket_exists(self, bucket: str) -> bool:
        self.calls.append(("bucket_exists", bucket))
        return False

    def make_bucket(self, bucket: str) -> None:
        self.calls.append(("make_bucket", bucket))

    def fput_object(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("put", *args, kwargs))

    def fget_object(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("get", *args, kwargs))

    def remove_object(self, *args: object) -> None:
        self.calls.append(("remove", *args))

    def presigned_get_object(self, *args: object, **kwargs: object) -> str:
        self.calls.append(("presign", *args, kwargs))
        return "https://objects.example/artifact"

    def _create_multipart_upload(
        self, bucket: str, object_key: str, headers: dict[str, str]
    ) -> str:
        self.calls.append(("create_multipart", bucket, object_key, headers))
        return "upload-id"

    def get_presigned_url(self, *args: object, **kwargs: object) -> str:
        self.calls.append(("presign_part", *args, kwargs))
        return "https://objects.example/upload-part"

    def _complete_multipart_upload(
        self,
        bucket: str,
        object_key: str,
        upload_id: str,
        parts: list[MultipartUploadPart],
    ) -> SimpleNamespace:
        normalized = tuple((part.part_number, part.etag) for part in parts)
        self.calls.append(
            ("complete_multipart", bucket, object_key, upload_id, normalized)
        )
        return SimpleNamespace(etag="completed-etag")

    def _abort_multipart_upload(
        self, bucket: str, object_key: str, upload_id: str
    ) -> None:
        self.calls.append(("abort_multipart", bucket, object_key, upload_id))

    def _list_multipart_uploads(self, bucket: str, **kwargs: object) -> SimpleNamespace:
        self.calls.append(("list_multipart", bucket, kwargs))
        return SimpleNamespace(
            uploads=[
                SimpleNamespace(
                    object_name="quarantine/video/resource/1/source",
                    upload_id="stale-upload",
                    initiated_time=datetime(2026, 8, 14, tzinfo=UTC),
                )
            ]
        )


def settings() -> Settings:
    return Settings(
        app_env="test",
        minio_access_key=SecretStr("access"),
        minio_secret_key=SecretStr("secret"),
    )


async def test_storage_uses_private_and_public_clients(tmp_path: Path) -> None:
    private = FakeMinio()
    public = FakeMinio()
    storage = MinioObjectStorage(settings(), private=private, public=public)
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video")
    target = tmp_path / "download.mp4"

    await storage.ensure_bucket()
    await storage.upload("jobs/one/video.mp4", source, "video/mp4")
    await storage.download("jobs/one/video.mp4", target)
    url = await storage.presigned_download(
        "jobs/one/video.mp4", title="example", ttl_seconds=60
    )
    await storage.delete("jobs/one/video.mp4")

    assert ("make_bucket", "video-artifacts") in private.calls
    assert any(call[0] == "put" for call in private.calls)
    assert any(call[0] == "get" for call in private.calls)
    assert any(call[0] == "remove" for call in private.calls)
    presign = next(call for call in public.calls if call[0] == "presign")
    options = presign[-1]
    assert isinstance(options, dict)
    assert options["response_headers"] == {
        "response-content-disposition": 'attachment; filename="example.mp4"'
    }
    assert url == "https://objects.example/artifact"


async def test_storage_uses_video_title_in_content_disposition() -> None:
    public = FakeMinio()
    storage = MinioObjectStorage(settings(), private=FakeMinio(), public=public)

    await storage.presigned_download(
        "downloads/job-1/1/video.mp4", title="Q4 Showreel", ttl_seconds=60
    )

    assert _signed_disposition(public) == 'attachment; filename="Q4 Showreel.mp4"'


async def test_storage_encodes_cjk_title_with_rfc5987() -> None:
    public = FakeMinio()
    storage = MinioObjectStorage(settings(), private=FakeMinio(), public=public)

    await storage.presigned_download(
        "downloads/job-1/1/video.mp4",
        title="【官方 MV】Never Gonna Give You Up - Rick Astley",
        ttl_seconds=60,
    )

    disposition = _signed_disposition(public)
    assert disposition.startswith('attachment; filename="video.mp4"; filename*=')
    assert "UTF-8''" in disposition
    assert "%E3%80%90%E5%AE%98%E6%96%B9" in disposition


async def test_storage_uses_plain_title_when_ascii() -> None:
    public = FakeMinio()
    storage = MinioObjectStorage(settings(), private=FakeMinio(), public=public)

    await storage.presigned_download(
        "downloads/job-1/1/video.mp4", title="Build Notes", ttl_seconds=60
    )

    assert _signed_disposition(public) == 'attachment; filename="Build Notes.mp4"'


async def test_storage_falls_back_when_title_empty() -> None:
    public = FakeMinio()
    storage = MinioObjectStorage(settings(), private=FakeMinio(), public=public)

    await storage.presigned_download(
        "downloads/job-1/1/video.mp4", title="", ttl_seconds=60
    )

    assert _signed_disposition(public) == 'attachment; filename="video.mp4"'


def _signed_disposition(public: FakeMinio) -> str:
    presign = next(call for call in public.calls if call[0] == "presign")
    options = presign[-1]
    assert isinstance(options, dict)
    return str(options["response_headers"]["response-content-disposition"])


async def test_storage_rejects_unsafe_object_keys(tmp_path: Path) -> None:
    storage = MinioObjectStorage(settings(), private=FakeMinio(), public=FakeMinio())

    with pytest.raises(ValueError, match="unsafe object key"):
        await storage.upload("../secret", tmp_path / "missing", "video/mp4")


async def test_private_storage_cannot_sign_public_downloads() -> None:
    storage = MinioObjectStorage(settings(), private=FakeMinio())

    with pytest.raises(RuntimeError, match="public download signing is not enabled"):
        await storage.presigned_download("jobs/one/video.mp4", ttl_seconds=60)


async def test_import_worker_can_disable_public_signing_client() -> None:
    storage = MinioObjectStorage.for_imports(
        settings(), private=FakeMinio(), enable_public_signing=False
    )

    with pytest.raises(RuntimeError, match="public download signing is not enabled"):
        await storage.presigned_download("downloads/job-1/1/video.mp4", ttl_seconds=60)


async def test_storage_controls_one_deterministic_multipart_upload() -> None:
    private = FakeMinio()
    public = FakeMinio()
    storage = MinioObjectStorage(settings(), private=private, public=public)
    object_key = "quarantine/video/4f7f4a1d/1/source"
    digest = "a" * 64

    upload_id = await storage.create_multipart_upload(
        object_key,
        content_type="video/mp4",
        declared_sha256=digest,
    )
    url = await storage.presign_upload_part(
        object_key,
        upload_id,
        2,
        ttl_seconds=900,
    )
    etag = await storage.complete_multipart_upload(
        object_key,
        upload_id,
        (
            _multipart_part(2, '"22222222222222222222222222222222"'),
            _multipart_part(1, "11111111111111111111111111111111"),
        ),
    )
    await storage.abort_multipart_upload(object_key, upload_id)

    assert upload_id == "upload-id"
    assert url == "https://objects.example/upload-part"
    assert etag == "completed-etag"
    assert (
        "create_multipart",
        "video-artifacts",
        object_key,
        {
            "Content-Type": "video/mp4",
            "X-Amz-Meta-Declared-Sha256": digest,
        },
    ) in private.calls
    assert (
        "complete_multipart",
        "video-artifacts",
        object_key,
        "upload-id",
        (
            (1, "11111111111111111111111111111111"),
            (2, "22222222222222222222222222222222"),
        ),
    ) in private.calls
    presign = next(call for call in public.calls if call[0] == "presign_part")
    assert presign[1:4] == ("PUT", "video-artifacts", object_key)
    assert presign[-1]["extra_query_params"] == {
        "partNumber": "2",
        "uploadId": "upload-id",
    }
    assert (
        "abort_multipart",
        "video-artifacts",
        object_key,
        "upload-id",
    ) in private.calls


async def test_storage_lists_bounded_incomplete_uploads_for_reconciliation() -> None:
    private = FakeMinio()
    storage = MinioObjectStorage(settings(), private=private)

    uploads = await storage.list_incomplete_multipart_uploads("quarantine/", limit=20)

    assert len(uploads) == 1
    assert uploads[0].object_key == "quarantine/video/resource/1/source"
    assert uploads[0].upload_id == "stale-upload"
    assert uploads[0].initiated_at == datetime(2026, 8, 14, tzinfo=UTC)
    assert (
        "list_multipart",
        "video-artifacts",
        {"prefix": "quarantine/", "max_uploads": 20},
    ) in private.calls


@pytest.mark.parametrize(
    ("part_number", "etag"),
    ((0, "1" * 32), (1, "not-an-etag")),
)
async def test_storage_rejects_invalid_multipart_parts(
    part_number: int, etag: str
) -> None:
    storage = MinioObjectStorage(settings(), private=FakeMinio())

    with pytest.raises(ValueError):
        await storage.complete_multipart_upload(
            "quarantine/video/resource/1/source",
            "upload-id",
            (_multipart_part(part_number, etag),),
        )


class PromotionMinio(FakeMinio):
    def __init__(self) -> None:
        super().__init__()
        self.objects: dict[str, SimpleNamespace] = {
            "quarantine/video/resource/1/source": SimpleNamespace(
                size=5,
                metadata={"x-amz-meta-declared-sha256": "0" * 64},
                content_type="video/mp4",
            )
        }

    def stat_object(self, bucket: str, object_key: str) -> SimpleNamespace:
        self.calls.append(("stat", bucket, object_key))
        try:
            return self.objects[object_key]
        except KeyError as exc:
            raise SimpleStorageError("NoSuchKey") from exc

    def copy_object(
        self,
        bucket: str,
        destination_key: str,
        source: CopySource,
        **kwargs: object,
    ) -> None:
        source_key = source.object_name
        source_object = self.objects[source_key]
        metadata = kwargs["metadata"]
        assert isinstance(metadata, dict)
        self.objects[destination_key] = SimpleNamespace(
            size=source_object.size,
            metadata={"x-amz-meta-sha256": metadata["sha256"]},
            content_type=metadata["Content-Type"],
        )
        self.calls.append(("copy", bucket, source_key, destination_key, kwargs))


class SimpleStorageError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


class ErrorMinio(FakeMinio):
    def __init__(self, code: str) -> None:
        super().__init__()
        self.code = code

    def _complete_multipart_upload(
        self,
        bucket: str,
        object_key: str,
        upload_id: str,
        parts: list[MultipartUploadPart],
    ) -> SimpleNamespace:
        raise SimpleStorageError(self.code)

    def _abort_multipart_upload(
        self, bucket: str, object_key: str, upload_id: str
    ) -> None:
        raise SimpleStorageError(self.code)

    def stat_object(self, bucket: str, object_key: str) -> SimpleNamespace:
        raise SimpleStorageError(self.code)


@pytest.mark.parametrize(
    ("code", "error_type"),
    (
        ("InvalidPart", MultipartUploadRejected),
        ("InvalidPartOrder", MultipartUploadRejected),
        ("EntityTooSmall", MultipartUploadRejected),
        ("NoSuchUpload", MultipartUploadNotFound),
        ("AccessDenied", ImportObjectStorageError),
    ),
)
async def test_storage_translates_multipart_completion_errors(
    code: str, error_type: type[Exception]
) -> None:
    storage = MinioObjectStorage(settings(), private=ErrorMinio(code))

    with pytest.raises(error_type):
        await storage.complete_multipart_upload(
            "quarantine/video/resource/1/source",
            "upload-id",
            (_multipart_part(1, "1" * 32),),
        )


async def test_storage_abort_is_idempotent_when_upload_is_missing() -> None:
    storage = MinioObjectStorage(settings(), private=ErrorMinio("NoSuchUpload"))

    await storage.abort_multipart_upload(
        "quarantine/video/resource/1/source", "upload-id"
    )


async def test_storage_translates_head_access_error() -> None:
    storage = MinioObjectStorage(settings(), private=ErrorMinio("AccessDenied"))

    with pytest.raises(ImportObjectStorageError) as captured:
        await storage.stat("quarantine/video/resource/1/source")

    assert getattr(captured.value.__cause__, "code", None) == "AccessDenied"


async def test_storage_promotes_verified_object_idempotently() -> None:
    private = PromotionMinio()
    storage = MinioObjectStorage(settings(), private=private)
    source_key = "quarantine/video/resource/1/source"
    destination_key = "downloads/job/1/video.mp4"
    digest = "b" * 64

    first = await storage.promote(
        source_key,
        destination_key,
        expected_size_bytes=5,
        sha256=digest,
        content_type="video/mp4",
    )
    second = await storage.promote(
        source_key,
        destination_key,
        expected_size_bytes=5,
        sha256=digest,
        content_type="video/mp4",
    )

    assert first == second
    assert (first.size_bytes, first.sha256, first.content_type) == (
        5,
        digest,
        "video/mp4",
    )
    assert len([call for call in private.calls if call[0] == "copy"]) == 1


def _multipart_part(part_number: int, etag: str) -> MultipartUploadPart:
    return MultipartUploadPart(part_number=part_number, etag=etag)
