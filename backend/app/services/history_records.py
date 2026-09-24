"""Read the user's parse and video analysis records as one history."""

import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from cryptography.fernet import InvalidToken

from app.services.downloads.inspection_models import EncryptedUrl
from app.services.downloads.ports import RequestFingerprinter, UrlCipher
from app.services.downloads.validation import validate_owner_hash


class HistoryRecordKind(StrEnum):
    PARSE = "parse"
    VIDEO_ANALYSIS = "video_analysis"


@dataclass(frozen=True, slots=True)
class HistoryRecordCursor:
    created_at: datetime
    record_type: HistoryRecordKind
    id: UUID


@dataclass(frozen=True, slots=True)
class HistoryRecordSnapshot:
    id: UUID
    record_type: HistoryRecordKind
    title: str | None
    created_at: datetime
    status: str
    version: int | None = None
    reason_code: str | None = None
    retry_at: datetime | None = None
    deadline: datetime | None = None
    inspection_id: UUID | None = None
    job_id: UUID | None = None
    download_id: UUID | None = None
    skill_id: str | None = None
    progress: int | None = None
    stage: str | None = None
    error_code: str | None = None
    encrypted_url: EncryptedUrl | None = field(default=None, repr=False)
    request_fingerprint: str | None = field(default=None, repr=False)
    access_policy: str | None = None


@dataclass(frozen=True, slots=True)
class HistoryRecordPage:
    items: tuple[HistoryRecordSnapshot, ...]
    next_cursor: HistoryRecordCursor | None


class HistoryRecordPersistence(Protocol):
    async def history(
        self,
        owner_hash: str,
        *,
        before: HistoryRecordCursor | None,
        limit: int,
    ) -> HistoryRecordPage: ...

    async def inspection_titles(
        self,
        owner_hash: str,
        fingerprints: frozenset[str],
        youtube_ids: frozenset[str],
    ) -> dict[str, str]: ...


class HistoryRecordService:
    def __init__(
        self,
        repository: HistoryRecordPersistence,
        cipher: UrlCipher,
        fingerprinter: RequestFingerprinter,
    ) -> None:
        self._repository = repository
        self._cipher = cipher
        self._fingerprinter = fingerprinter

    async def list(
        self,
        owner_hash: str,
        *,
        before: HistoryRecordCursor | None = None,
        limit: int = 20,
    ) -> HistoryRecordPage:
        validate_owner_hash(owner_hash)
        if not 1 <= limit <= 50:
            raise ValueError("invalid history page size")
        page = await self._repository.history(owner_hash, before=before, limit=limit)
        sources: dict[UUID, tuple[str, str | None, str]] = {}
        for item in page.items:
            if item.record_type is not HistoryRecordKind.PARSE or item.title:
                continue
            if item.encrypted_url is None or item.request_fingerprint is None:
                continue
            try:
                url = self._cipher.decrypt(item.encrypted_url)
            except (InvalidToken, ValueError, UnicodeDecodeError):
                continue
            if item.access_policy is not None:
                inspection_fingerprint = self._fingerprinter.fingerprint(
                    "inspection", url, item.access_policy
                )
                sources[item.id] = (
                    inspection_fingerprint,
                    _youtube_id(url),
                    _source_label(url, item.request_fingerprint),
                )

        titles = (
            await self._repository.inspection_titles(
                owner_hash,
                frozenset(source[0] for source in sources.values()),
                frozenset(source[1] for source in sources.values() if source[1]),
            )
            if sources
            else {}
        )
        display_titles = {
            item_id: titles.get(fingerprint)
            or (titles.get(media_id) if media_id else None)
            or source_label
            for item_id, (fingerprint, media_id, source_label) in sources.items()
        }
        items = tuple(
            replace(
                item,
                title=display_titles.get(
                    item.id,
                    item.title or _unavailable_source_label(item.request_fingerprint),
                ),
                encrypted_url=None,
            )
            if item.record_type is HistoryRecordKind.PARSE
            else item
            for item in page.items
        )
        return HistoryRecordPage(items, page.next_cursor)


_YOUTUBE_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")


def _source_label(url: str, fingerprint: str) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    media_id = _youtube_id(url)
    if media_id is not None:
        return f"YouTube · {media_id}"
    return f"{host or '媒体解析'} · {fingerprint[:8]}"


def _youtube_id(url: str) -> str | None:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    media_id: str | None = None
    if host == "youtu.be":
        media_id = parsed.path.strip("/")
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            media_id = parse_qs(parsed.query).get("v", [None])[0]
        elif parsed.path.startswith(("/shorts/", "/live/")):
            media_id = parsed.path.split("/")[2]
    if media_id is not None and _YOUTUBE_ID.fullmatch(media_id):
        return media_id
    return None


def _unavailable_source_label(fingerprint: str | None) -> str:
    return f"媒体解析 · {fingerprint[:8]}" if fingerprint else "媒体解析"
