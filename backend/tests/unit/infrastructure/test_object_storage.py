from __future__ import annotations

from pathlib import Path

import pytest
from app.core.config import Settings
from app.infrastructure.object_storage import MinioObjectStorage
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
