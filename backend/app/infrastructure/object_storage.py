"""Private MinIO storage with optional public download signing."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from minio import Minio
from minio.commonconfig import REPLACE, CopySource
from minio.datatypes import Part

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class StoredObjectStat:
    size_bytes: int
    sha256: str | None
    content_type: str | None = None


@dataclass(frozen=True, slots=True)
class StoredObject:
    object_key: str
    last_modified: datetime


@dataclass(frozen=True, slots=True)
class MultipartUploadPart:
    part_number: int
    etag: str


@dataclass(frozen=True, slots=True)
class IncompleteMultipartUpload:
    object_key: str
    upload_id: str
    initiated_at: datetime


class MinioObjectStorage:
    def __init__(
        self,
        settings: Settings,
        *,
        private: Minio | None = None,
        public: Minio | None = None,
        enable_public_signing: bool = False,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        if (access_key is None) != (secret_key is None):
            raise ValueError("MinIO access and secret keys must be configured together")
        access_key = access_key or settings.minio_access_key.get_secret_value()
        secret_key = secret_key or settings.minio_secret_key.get_secret_value()
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

    @classmethod
    def for_imports(
        cls,
        settings: Settings,
        *,
        private: Minio | None = None,
        public: Minio | None = None,
    ) -> MinioObjectStorage:
        """Build storage with the quarantine-scoped import identity."""
        return cls(
            settings,
            private=private,
            public=public,
            enable_public_signing=True,
            access_key=settings.minio_import_access_key.get_secret_value(),
            secret_key=settings.minio_import_secret_key.get_secret_value(),
        )

    @property
    def bucket(self) -> str:
        return self._bucket

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
        return StoredObjectStat(
            size_bytes=result.size,
            sha256=sha256,
            content_type=getattr(result, "content_type", None),
        )

    async def create_multipart_upload(
        self,
        object_key: str,
        *,
        content_type: str,
        declared_sha256: str | None = None,
    ) -> str:
        """Create a multipart upload for one server-selected object key.

        The MinIO Python SDK currently exposes multipart control primitives as
        private methods. They are isolated here so the application port remains
        stable if the pinned SDK changes its implementation.
        """
        _validate_key(object_key)
        _validate_content_type(content_type)
        headers: dict[str, str | list[str] | tuple[str]] = {
            "Content-Type": content_type
        }
        if declared_sha256 is not None:
            headers["X-Amz-Meta-Declared-Sha256"] = _validate_sha256(declared_sha256)
        upload_id = await asyncio.to_thread(
            self._private._create_multipart_upload,
            self._bucket,
            object_key,
            headers,
        )
        return _validate_upload_id(upload_id)

    async def presign_upload_part(
        self,
        object_key: str,
        upload_id: str,
        part_number: int,
        *,
        ttl_seconds: int,
    ) -> str:
        _validate_key(object_key)
        upload_id = _validate_upload_id(upload_id)
        if self._public is None:
            raise RuntimeError("public upload signing is not enabled")
        if isinstance(part_number, bool) or not 1 <= part_number <= 10_000:
            raise ValueError("part number must be between 1 and 10000")
        if isinstance(ttl_seconds, bool) or not 1 <= ttl_seconds <= 604_800:
            raise ValueError("upload signing TTL must be between 1 and 604800")
        return await asyncio.to_thread(
            self._public.get_presigned_url,
            "PUT",
            self._bucket,
            object_key,
            expires=timedelta(seconds=ttl_seconds),
            extra_query_params={
                "partNumber": str(part_number),
                "uploadId": upload_id,
            },
        )

    async def complete_multipart_upload(
        self,
        object_key: str,
        upload_id: str,
        parts: tuple[MultipartUploadPart, ...],
    ) -> str | None:
        _validate_key(object_key)
        upload_id = _validate_upload_id(upload_id)
        normalized = _normalize_multipart_parts(parts)
        result = await asyncio.to_thread(
            self._private._complete_multipart_upload,
            self._bucket,
            object_key,
            upload_id,
            normalized,
        )
        return getattr(result, "etag", None)

    async def abort_multipart_upload(self, object_key: str, upload_id: str) -> None:
        _validate_key(object_key)
        upload_id = _validate_upload_id(upload_id)
        await asyncio.to_thread(
            self._private._abort_multipart_upload,
            self._bucket,
            object_key,
            upload_id,
        )

    async def list_incomplete_multipart_uploads(
        self, prefix: str, *, limit: int = 1000
    ) -> tuple[IncompleteMultipartUpload, ...]:
        """Return one bounded reconciliation page of incomplete uploads."""
        _validate_key(prefix)
        if isinstance(limit, bool) or not 1 <= limit <= 1000:
            raise ValueError("multipart list limit must be between 1 and 1000")
        result = await asyncio.to_thread(
            self._private._list_multipart_uploads,
            self._bucket,
            prefix=prefix,
            max_uploads=limit,
        )
        uploads: list[IncompleteMultipartUpload] = []
        for item in result.uploads:
            if item.upload_id is None or item.initiated_time is None:
                raise RuntimeError("object storage returned incomplete upload metadata")
            uploads.append(
                IncompleteMultipartUpload(
                    object_key=item.object_name,
                    upload_id=item.upload_id,
                    initiated_at=item.initiated_time,
                )
            )
        return tuple(uploads)

    async def promote(
        self,
        source_key: str,
        destination_key: str,
        *,
        expected_size_bytes: int,
        sha256: str,
        content_type: str,
    ) -> StoredObjectStat:
        """Idempotently copy a verified object to its deterministic final key.

        The quarantine source is intentionally retained. Its deletion belongs to
        post-commit cleanup/reconciliation so a database failure cannot lose the
        only recoverable copy.
        """
        _validate_key(source_key)
        _validate_key(destination_key)
        if source_key == destination_key:
            raise ValueError("source and destination object keys must differ")
        if isinstance(expected_size_bytes, bool) or expected_size_bytes <= 0:
            raise ValueError("expected object size must be positive")
        sha256 = _validate_sha256(sha256)
        _validate_content_type(content_type)

        current = await self.stat(destination_key)
        if current is not None:
            if (current.size_bytes, current.sha256, current.content_type) != (
                expected_size_bytes,
                sha256,
                content_type,
            ):
                raise RuntimeError("destination object conflicts with promotion")
            return current

        source = await self.stat(source_key)
        if source is None or source.size_bytes != expected_size_bytes:
            raise RuntimeError("source object conflicts with promotion")
        await asyncio.to_thread(
            self._private.copy_object,
            self._bucket,
            destination_key,
            CopySource(self._bucket, source_key),
            metadata={"Content-Type": content_type, "sha256": sha256},
            metadata_directive=REPLACE,
        )
        promoted = await self.stat(destination_key)
        if promoted is None or (promoted.size_bytes, promoted.sha256) != (
            expected_size_bytes,
            sha256,
        ):
            raise RuntimeError("promoted object failed verification")
        return promoted

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

    async def presigned_download(
        self, object_key: str, *, title: str | None = None, ttl_seconds: int
    ) -> str:
        _validate_key(object_key)
        if self._public is None:
            raise RuntimeError("public download signing is not enabled")
        return await asyncio.to_thread(
            self._public.presigned_get_object,
            self._bucket,
            object_key,
            expires=timedelta(seconds=ttl_seconds),
            response_headers={
                "response-content-disposition": _download_disposition(object_key, title)
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


def _validate_upload_id(upload_id: str) -> str:
    if (
        not isinstance(upload_id, str)
        or not upload_id
        or len(upload_id) > 1024
        or any(ord(character) < 0x20 for character in upload_id)
    ):
        raise ValueError("invalid multipart upload id")
    return upload_id


def _validate_sha256(value: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("SHA-256 must be lowercase hexadecimal")
    return value


def _validate_content_type(value: str) -> None:
    if (
        not value
        or len(value) > 255
        or value != value.strip()
        or "\r" in value
        or "\n" in value
        or "/" not in value
    ):
        raise ValueError("invalid content type")


def _normalize_multipart_parts(parts: tuple[MultipartUploadPart, ...]) -> list[Part]:
    if not parts or len(parts) > 10_000:
        raise ValueError("multipart completion requires between 1 and 10000 parts")
    normalized: list[Part] = []
    seen: set[int] = set()
    for item in parts:
        if (
            isinstance(item.part_number, bool)
            or not 1 <= item.part_number <= 10_000
            or item.part_number in seen
        ):
            raise ValueError("multipart part numbers must be unique and in range")
        etag = item.etag.removeprefix('"').removesuffix('"')
        if re.fullmatch(r"[0-9a-fA-F]{32}", etag) is None:
            raise ValueError("invalid multipart part ETag")
        seen.add(item.part_number)
        normalized.append(Part(item.part_number, etag.lower()))
    return sorted(normalized, key=lambda item: item.part_number)


def _download_filename(object_key: str) -> str:
    suffix = PurePosixPath(object_key).suffix.casefold()
    return f"video{suffix}" if suffix in {".mp4", ".webm"} else "download"


def _download_disposition(object_key: str, title: str | None) -> str:
    """Build an RFC 6266 attachment disposition using the video title.

    Non-ASCII titles use RFC 5987 ``filename*=UTF-8''...`` encoding so browsers
    save the file with a readable name; an ASCII ``filename=`` fallback is always
    included so legacy agents still get a name.
    """
    fallback = _download_filename(object_key)
    clean_title = _sanitize_filename(title) if title else ""
    if not clean_title:
        return f'attachment; filename="{fallback}"'
    extension = PurePosixPath(object_key).suffix
    encoded_name = f"{clean_title}{extension}"
    if encoded_name.isascii():
        return f'attachment; filename="{encoded_name}"'
    return (
        f'attachment; filename="{fallback}"; '
        f"filename*=UTF-8''{quote(encoded_name, safe='')}"
    )


def _sanitize_filename(title: str) -> str:
    value = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]', "", title).strip()
    return value[:128].rstrip(".") if value else ""
