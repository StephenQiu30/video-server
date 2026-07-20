"""Small MinIO client used for private artifact storage.

The application uses MinIO directly in the MVP.  Uploads use the service
endpoint while presigned URLs are created from the browser-facing endpoint so
the internal Docker hostname is never returned to the web client.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Any, BinaryIO

from minio import Minio
from minio.error import S3Error


class MinioStorage:
    """MinIO-backed artifact store with a deliberately small API."""

    def __init__(self, settings: Any) -> None:
        secure = bool(settings.minio_secure)
        self.bucket = str(settings.minio_bucket)
        self._client = Minio(
            str(settings.minio_endpoint),
            access_key=str(settings.minio_access_key),
            secret_key=str(settings.minio_secret_key),
            secure=secure,
        )
        self._public_client = Minio(
            str(settings.minio_public_endpoint),
            access_key=str(settings.minio_access_key),
            secret_key=str(settings.minio_secret_key),
            secure=secure,
        )
        self._presigned_ttl = int(settings.minio_presigned_url_ttl_seconds)

    async def ensure_bucket(self) -> None:
        exists = await asyncio.to_thread(self._client.bucket_exists, self.bucket)
        if not exists:
            await asyncio.to_thread(self._client.make_bucket, self.bucket)

    async def healthcheck(self) -> bool:
        try:
            await self.ensure_bucket()
            return True
        except (OSError, S3Error):
            return False

    async def put_file(
        self,
        object_key: str,
        file_path: str | Path,
        *,
        content_type: str,
        size_bytes: int | None = None,
    ) -> None:
        path = Path(file_path)
        length = int(size_bytes if size_bytes is not None else path.stat().st_size)

        def upload() -> None:
            with path.open("rb") as source:
                self._client.put_object(
                    self.bucket,
                    object_key,
                    source,
                    length,
                    content_type=content_type,
                )

        await asyncio.to_thread(upload)

    async def put_stream(
        self,
        object_key: str,
        source: BinaryIO,
        *,
        size_bytes: int,
        content_type: str,
    ) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            self.bucket,
            object_key,
            source,
            int(size_bytes),
            content_type=content_type,
        )

    async def presigned_download(
        self,
        object_key: str,
        *,
        expires_seconds: int | None = None,
        response_filename: str | None = None,
    ) -> str:
        response_headers: dict[str, str | list[str] | tuple[str]] | None = None
        if response_filename:
            # The filename is normalized before reaching this adapter.  Keep
            # the header value quoted and avoid reflecting arbitrary headers.
            safe_name = response_filename.replace('"', "'")
            response_headers = {
                "response-content-disposition": f'attachment; filename="{safe_name}"'
            }
        return await asyncio.to_thread(
            self._public_client.presigned_get_object,
            self.bucket,
            object_key,
            expires=timedelta(seconds=expires_seconds or self._presigned_ttl),
            response_headers=response_headers,
        )

    async def remove(self, object_key: str) -> None:
        await asyncio.to_thread(self._client.remove_object, self.bucket, object_key)


__all__ = ["MinioStorage"]
