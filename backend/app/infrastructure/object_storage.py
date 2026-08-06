"""Private MinIO storage with optional public download signing."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path, PurePosixPath

from minio import Minio

from app.core.config import Settings


class MinioObjectStorage:
    def __init__(
        self,
        settings: Settings,
        *,
        private: Minio | None = None,
        public: Minio | None = None,
        enable_public_signing: bool = False,
    ) -> None:
        access_key = settings.minio_access_key.get_secret_value()
        secret_key = settings.minio_secret_key.get_secret_value()
        self._bucket = settings.minio_bucket
        self._private = private or Minio(
            settings.minio_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=settings.minio_internal_secure,
            region=settings.minio_region,
        )
        self._public = public
        if self._public is None and enable_public_signing:
            self._public = Minio(
                settings.minio_public_endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=settings.minio_public_secure,
                region=settings.minio_region,
            )

    async def ensure_bucket(self) -> None:
        exists = await asyncio.to_thread(self._private.bucket_exists, self._bucket)
        if not exists:
            await asyncio.to_thread(self._private.make_bucket, self._bucket)

    async def upload(self, object_key: str, source: Path, content_type: str) -> int:
        _validate_key(object_key)
        size = source.stat().st_size
        await asyncio.to_thread(
            self._private.fput_object,
            self._bucket,
            object_key,
            str(source),
            content_type=content_type,
        )
        return size

    async def download(self, object_key: str, target: Path) -> None:
        _validate_key(object_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(
            self._private.fget_object,
            self._bucket,
            object_key,
            str(target),
        )

    async def presigned_download(self, object_key: str, *, ttl_seconds: int) -> str:
        _validate_key(object_key)
        if self._public is None:
            raise RuntimeError("public download signing is not enabled")
        return await asyncio.to_thread(
            self._public.presigned_get_object,
            self._bucket,
            object_key,
            expires=timedelta(seconds=ttl_seconds),
        )

    async def delete(self, object_key: str) -> None:
        _validate_key(object_key)
        await asyncio.to_thread(self._private.remove_object, self._bucket, object_key)


def _validate_key(object_key: str) -> None:
    path = PurePosixPath(object_key)
    unsafe = (
        not object_key
        or object_key.startswith("/")
        or any(part in {"", ".", ".."} for part in path.parts)
    )
    if unsafe:
        raise ValueError("unsafe object key")
