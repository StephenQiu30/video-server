"""Private MinIO storage with optional public download signing."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path, PurePosixPath

from minio import Minio

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class StoredObjectStat:
    size_bytes: int
    sha256: str | None


@dataclass(frozen=True, slots=True)
class StoredObject:
    object_key: str
    last_modified: datetime


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

    async def upload_bytes(
        self, object_key: str, content: bytes, content_type: str, sha256: str
    ) -> int:
        _validate_key(object_key)
        if not content:
            raise ValueError("object content cannot be empty")
        await asyncio.to_thread(
            self._private.put_object,
            self._bucket,
            object_key,
            BytesIO(content),
            len(content),
            content_type=content_type,
            metadata={"sha256": sha256},
        )
        return len(content)

    async def stat(self, object_key: str) -> StoredObjectStat | None:
        _validate_key(object_key)
        try:
            result = await asyncio.to_thread(
                self._private.stat_object, self._bucket, object_key
            )
        except Exception as error:
            if getattr(error, "code", None) in {"NoSuchKey", "NoSuchObject"}:
                return None
            raise
        metadata = getattr(result, "metadata", {}) or {}
        sha256 = metadata.get("x-amz-meta-sha256") or metadata.get("sha256")
        if result.size is None:
            raise RuntimeError("object storage returned no size")
        return StoredObjectStat(size_bytes=result.size, sha256=sha256)

    async def read(self, object_key: str) -> bytes:
        _validate_key(object_key)
        response = await asyncio.to_thread(
            self._private.get_object, self._bucket, object_key
        )
        try:
            return await asyncio.to_thread(response.read)
        finally:
            response.close()
            response.release_conn()

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
            response_headers={
                "response-content-disposition": (
                    f'attachment; filename="{_download_filename(object_key)}"'
                )
            },
        )

    async def delete(self, object_key: str) -> None:
        _validate_key(object_key)
        await asyncio.to_thread(self._private.remove_object, self._bucket, object_key)

    async def list(self, prefix: str) -> tuple[StoredObject, ...]:
        _validate_key(prefix)

        def collect() -> tuple[StoredObject, ...]:
            return tuple(
                StoredObject(item.object_name, item.last_modified)
                for item in self._private.list_objects(
                    self._bucket, prefix=prefix, recursive=True
                )
                if item.object_name is not None and item.last_modified is not None
            )

        return await asyncio.to_thread(collect)


def _validate_key(object_key: str) -> None:
    path = PurePosixPath(object_key)
    unsafe = (
        not object_key
        or object_key.startswith("/")
        or any(part in {"", ".", ".."} for part in path.parts)
    )
    if unsafe:
        raise ValueError("unsafe object key")


def _download_filename(object_key: str) -> str:
    suffix = PurePosixPath(object_key).suffix.casefold()
    return f"video{suffix}" if suffix in {".mp4", ".webm"} else "download"
