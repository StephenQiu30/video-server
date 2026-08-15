"""Bounded delivery of a native Runner artifact to a presigned object URL."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from app.runner.errors import RunnerFailure

_CHUNK_SIZE = 1024 * 1024


async def upload_presigned_artifact(
    source: Path,
    upload_url: str,
    *,
    allowed_origins: frozenset[str],
    timeout_seconds: float,
) -> None:
    origin = _origin(upload_url)
    if origin not in allowed_origins:
        raise RunnerFailure("artifact_delivery_rejected", status=422)
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise RunnerFailure("artifact_delivery_failed", status=502) from exc
    if size <= 0:
        raise RunnerFailure("artifact_delivery_failed", status=502)

    async def chunks() -> AsyncIterator[bytes]:
        with source.open("rb") as artifact:
            while chunk := artifact.read(_CHUNK_SIZE):
                yield chunk

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(timeout_seconds),
            trust_env=False,
        ) as client:
            response = await client.put(
                upload_url,
                headers={"Content-Length": str(size)},
                content=chunks(),
            )
    except (OSError, httpx.HTTPError) as exc:
        raise RunnerFailure("artifact_delivery_failed", status=503) from exc
    if response.status_code not in {200, 201, 204}:
        raise RunnerFailure("artifact_delivery_failed", status=502)


def _origin(url: str) -> str:
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError as exc:
        raise RunnerFailure("artifact_delivery_rejected", status=422) from exc
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise RunnerFailure("artifact_delivery_rejected", status=422)
    return f"{parsed.scheme}://{parsed.netloc}"
