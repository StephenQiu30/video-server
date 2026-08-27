"""Best-effort thumbnail recovery from a verified local video artifact."""

from __future__ import annotations

import asyncio
import base64
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

ProcessRunner = Callable[[tuple[str, ...], float], Awaitable[bool]]

logger = logging.getLogger(__name__)


class ThumbnailPersister(Protocol):
    async def __call__(
        self, resource_id: UUID, owner_hash: str, data_url: str | None, /
    ) -> bool: ...


class ArtifactThumbnailRecovery:
    def __init__(
        self,
        persist: ThumbnailPersister,
        *,
        ffmpeg_binary: Path,
        timeout_seconds: float,
        max_bytes: int,
        run_process: ProcessRunner | None = None,
    ) -> None:
        if timeout_seconds <= 0 or max_bytes <= 0:
            raise ValueError("thumbnail recovery limits must be positive")
        self._persist = persist
        self._ffmpeg = ffmpeg_binary
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._run_process = run_process or _run_process

    async def recover(
        self,
        inspection_id: UUID,
        owner_hash: str,
        artifact: Path,
    ) -> bool:
        output = artifact.parent / f".thumbnail-{uuid4().hex}.jpg"
        command = (
            str(self._ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-protocol_whitelist",
            "file,crypto,data",
            "-i",
            str(artifact),
            "-frames:v",
            "1",
            "-vf",
            "scale=1280:-2:force_original_aspect_ratio=decrease",
            "-q:v",
            "3",
            "-f",
            "image2",
            "-y",
            str(output),
        )
        try:
            if not await self._run_process(command, self._timeout):
                return False
            content = await asyncio.to_thread(_read_jpeg, output, self._max_bytes)
            if content is None:
                return False
            encoded = base64.b64encode(content).decode("ascii")
            return await self._persist(
                inspection_id,
                owner_hash,
                f"data:image/jpeg;base64,{encoded}",
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(
                "thumbnail recovery failed for inspection %s",
                inspection_id,
                exc_info=True,
            )
            return False
        finally:
            output.unlink(missing_ok=True)


async def _run_process(command: tuple[str, ...], timeout_seconds: float) -> bool:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        async with asyncio.timeout(timeout_seconds):
            return await process.wait() == 0
    except TimeoutError:
        process.kill()
        await process.wait()
        return False
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise


def _read_jpeg(path: Path, max_bytes: int) -> bytes | None:
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size <= 0 or size > max_bytes:
        return None
    content = path.read_bytes()
    if len(content) != size or not content.startswith(b"\xff\xd8\xff"):
        return None
    return content
