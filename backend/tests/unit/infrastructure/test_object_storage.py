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
    url = await storage.presigned_download("jobs/one/video.mp4", ttl_seconds=60)
    await storage.delete("jobs/one/video.mp4")

    assert ("make_bucket", "video-artifacts") in private.calls
    assert any(call[0] == "put" for call in private.calls)
    assert any(call[0] == "get" for call in private.calls)
    assert any(call[0] == "remove" for call in private.calls)
    presign = next(call for call in public.calls if call[0] == "presign")
    options = presign[-1]
    assert isinstance(options, dict)
    assert options["response_headers"] == {
        "response-content-disposition": 'attachment; filename="video.mp4"'
    }
    assert url == "https://objects.example/artifact"


async def test_storage_rejects_unsafe_object_keys(tmp_path: Path) -> None:
    storage = MinioObjectStorage(settings(), private=FakeMinio(), public=FakeMinio())

    with pytest.raises(ValueError, match="unsafe object key"):
        await storage.upload("../secret", tmp_path / "missing", "video/mp4")


async def test_private_storage_cannot_sign_public_downloads() -> None:
    storage = MinioObjectStorage(settings(), private=FakeMinio())

    with pytest.raises(RuntimeError, match="public download signing is not enabled"):
        await storage.presigned_download("jobs/one/video.mp4", ttl_seconds=60)
