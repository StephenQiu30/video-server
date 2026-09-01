"""Bounded static HTML parser for public WeChat articles."""

from __future__ import annotations

import hashlib
import html
import json
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urlsplit

from app.application.source_discoveries import (
    ArticleAccessRestricted,
    ArticleDiscoveryCandidate,
    ArticleDiscoveryFailure,
    ArticleDiscoveryResult,
)
from app.domain.providers import ProviderKey
from app.domain.source_discovery import (
    DiscoveryDecisionHint,
    DiscoveryItemKind,
    DiscoveryItemStatus,
)

_MPVID = re.compile(r"wxv_[A-Za-z0-9_-]{4,128}")
_QQVIDEO_PATHS = (
    re.compile(r"/x/page/([A-Za-z0-9_-]{4,64})\.html"),
    re.compile(r"/x/cover/[A-Za-z0-9_-]{4,128}/([A-Za-z0-9_-]{4,64})\.html"),
)
_CHANNELS_PATH = re.compile(r"/sph/[A-Za-z0-9_-]{4,256}/?")
_TRANS_INFO = re.compile(r"\bmp_video_trans_info\b\s*=")
_RESTRICTED_MARKERS = (
    "环境异常",
    "访问过于频繁",
    "安全验证",
    "请输入验证码",
    "该内容为付费内容",
    "登录后继续",
)


class _ArticleHtmlParser(HTMLParser):
    def __init__(self, *, max_items: int) -> None:
        super().__init__(convert_charrefs=True)
        self.max_items = max_items
        self.title = ""
        self._in_title = False
        self._in_activity_title = False
        self.has_article_body = False
        self.embeds: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value or "" for key, value in attrs}
        tag = tag.casefold()
        if tag == "title":
            self._in_title = True
        if values.get("id") == "activity-name":
            self._in_activity_title = True
        if values.get("id") == "js_content":
            self.has_article_body = True
        if tag == "meta":
            key = (values.get("property") or values.get("name") or "").casefold()
            if key in {"og:title", "twitter:title"} and values.get("content"):
                self.title = values["content"]
        if tag in {"iframe", "mpvideo", "mp-common-videosnap", "video"}:
            if len(self.embeds) >= self.max_items:
                raise ArticleDiscoveryFailure("article embed limit exceeded")
            self.embeds.append((tag, values))

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self._in_title = False
        if tag.casefold() == "h1":
            self._in_activity_title = False

    def handle_data(self, data: str) -> None:
        if (self._in_title or self._in_activity_title) and not self.title:
            self.title = data


def parse_article_html(
    payload: str,
    *,
    max_items: int = 24,
    max_inline_bytes: int = 512 * 1024,
) -> ArticleDiscoveryResult:
    if not payload.strip():
        raise ArticleDiscoveryFailure("article HTML is empty")
    head = payload[:16_384]
    if any(marker in head for marker in _RESTRICTED_MARKERS):
        raise ArticleAccessRestricted("article access is restricted")
    parser = _ArticleHtmlParser(max_items=max_items)
    try:
        parser.feed(payload)
        parser.close()
    except (ValueError, ArticleDiscoveryFailure) as exc:
        raise ArticleDiscoveryFailure("article HTML is invalid") from exc
    if not parser.has_article_body:
        raise ArticleDiscoveryFailure("article body is unavailable")

    native_identity = _native_identity_map(payload, max_inline_bytes=max_inline_bytes)
    candidates: list[ArticleDiscoveryCandidate] = []
    seen: set[str] = set()
    for tag, attrs in parser.embeds:
        candidate = _classify_embed(tag, attrs, native_identity)
        if candidate.identity_evidence_hash in seen:
            continue
        seen.add(candidate.identity_evidence_hash)
        candidates.append(candidate)
    return ArticleDiscoveryResult(
        title=_sanitize(parser.title) or "微信公众号文章",
        items=tuple(candidates),
    )


def _classify_embed(
    tag: str,
    attrs: dict[str, str],
    native_identity: dict[str, bool],
) -> ArticleDiscoveryCandidate:
    mpvid = attrs.get("data-mpvid") or attrs.get("mpvid") or attrs.get("vid") or ""
    if _MPVID.fullmatch(mpvid):
        verified = native_identity.get(mpvid, False)
        return _candidate(
            DiscoveryItemKind.OFFICIAL_ACCOUNT_NATIVE,
            ProviderKey.WECHAT_OFFICIAL_ACCOUNT_ARTICLE,
            attrs.get("data-title") or attrs.get("title") or "公众号原生视频",
            f"native:{mpvid}",
            DiscoveryDecisionHint.CANDIDATE
            if verified
            else DiscoveryDecisionHint.UNSUPPORTED,
            DiscoveryItemStatus.READY
            if verified
            else DiscoveryItemStatus.IDENTITY_UNVERIFIED,
        )

    src = html.unescape(attrs.get("src") or attrs.get("data-src") or "").strip()
    parsed = urlsplit(src)
    host = (parsed.hostname or "").casefold()
    if host == "v.qq.com":
        media_id = next(
            (
                match.group(1)
                for pattern in _QQVIDEO_PATHS
                if (match := pattern.fullmatch(parsed.path)) is not None
            ),
            None,
        )
        if media_id is None and parsed.path in {
            "/iframe/preview.html",
            "/txp/iframe/player.html",
        }:
            query = parse_qs(parsed.query, keep_blank_values=True)
            values = query.get("vid", [])
            if len(values) == 1 and re.fullmatch(r"[A-Za-z0-9_-]{4,64}", values[0]):
                media_id = values[0]
        if media_id is not None:
            return _candidate(
                DiscoveryItemKind.TENCENT_VIDEO,
                ProviderKey.QQVIDEO,
                attrs.get("title") or "腾讯视频",
                f"qqvideo:{media_id}",
                DiscoveryDecisionHint.UNSUPPORTED,
                DiscoveryItemStatus.READY,
            )
    if tag == "mp-common-videosnap" or (
        host == "weixin.qq.com" and _CHANNELS_PATH.fullmatch(parsed.path)
    ):
        identity = attrs.get("data-id") or attrs.get("id") or parsed.path or tag
        return _candidate(
            DiscoveryItemKind.WECHAT_CHANNELS,
            ProviderKey.WECHAT_CHANNELS,
            attrs.get("data-title") or attrs.get("title") or "微信视频号内容",
            f"channels:{identity}",
            DiscoveryDecisionHint.EXPORT_REQUIRED,
            DiscoveryItemStatus.READY,
        )
    evidence = f"unknown:{tag}:{src[:512]}:{attrs.get('id', '')}"
    return _candidate(
        DiscoveryItemKind.UNKNOWN,
        None,
        attrs.get("title") or "未知嵌入视频",
        evidence,
        DiscoveryDecisionHint.UNSUPPORTED,
        DiscoveryItemStatus.IDENTITY_UNVERIFIED,
    )


def _candidate(
    kind: DiscoveryItemKind,
    child_provider: str | None,
    title: str,
    evidence: str,
    hint: DiscoveryDecisionHint,
    status: DiscoveryItemStatus,
) -> ArticleDiscoveryCandidate:
    return ArticleDiscoveryCandidate(
        kind=kind,
        child_provider=child_provider,
        title=_sanitize(title) or "文章视频",
        duration_ms=None,
        identity_evidence_hash=hashlib.sha256(evidence.encode()).hexdigest(),
        decision_hint=hint,
        status=status,
    )


def _native_identity_map(payload: str, *, max_inline_bytes: int) -> dict[str, bool]:
    if len(payload.encode(errors="ignore")) > max_inline_bytes * 8:
        return {}
    decoder = json.JSONDecoder()
    occurrences: dict[str, list[bool]] = {}
    for marker in _TRANS_INFO.finditer(payload):
        suffix = html.unescape(payload[marker.end() : marker.end() + max_inline_bytes])
        stripped = suffix.lstrip()
        if not stripped.startswith(("[", "{")):
            continue
        try:
            value, _ = decoder.raw_decode(stripped)
        except json.JSONDecodeError:
            continue
        for record in _walk_dicts(value):
            mpvid = record.get("mpvid")
            media_id = record.get("media_id")
            urls = tuple(_walk_strings(record))
            if not isinstance(mpvid, str) or not _MPVID.fullmatch(mpvid):
                continue
            valid = (
                isinstance(media_id, str)
                and bool(media_id.strip())
                and any(_is_qpic_mp4_url(url) for url in urls)
            )
            occurrences.setdefault(mpvid, []).append(valid)
    return {
        mpvid: len(matches) == 1 and matches[0]
        for mpvid, matches in occurrences.items()
    }


def _walk_dicts(value: object) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(_walk_dicts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_dicts(child))
    return found


def _walk_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _walk_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _walk_strings(child)]
    return []


def _is_qpic_mp4_url(value: str) -> bool:
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").casefold() == "mpvideo.qpic.cn"
        and parsed.path.casefold().endswith(".mp4")
    )


def _sanitize(value: str) -> str:
    return " ".join(html.unescape(value).split()).strip()[:200]
