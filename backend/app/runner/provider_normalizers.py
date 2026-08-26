"""Pure URL policies used by declarative provider profiles."""

from __future__ import annotations

import re
from urllib.parse import SplitResult, parse_qs

from app.runner.errors import RunnerFailure

_VIMEO_ID = re.compile(r"/([0-9]+)/?$")
_DOUYIN_VIDEO = re.compile(r"/video/(?P<id>[0-9]+)/?$")
_DOUYIN_SHARE = re.compile(r"/share/video/(?P<id>[0-9]+)/?$")
_KUAISHOU_VIDEO = re.compile(r"/short-video/(?P<id>[A-Za-z0-9]+)/?$")
_SNAPCHAT_SPOTLIGHT = re.compile(r"/spotlight/(?P<id>[A-Za-z0-9_-]+)/?$")
_LINKEDIN_POST = re.compile(
    r"/(?:posts/[^/]+-(?:activity|ugcpost)-[0-9]+-[^/]+"
    r"|feed/update/urn:li:(?:activity|ugcpost):[0-9]+)/?$",
    re.IGNORECASE,
)
_TELEGRAM_POST = re.compile(r"/(?:s/)?[A-Za-z0-9_]+/[0-9]+/?$")
_KICK_CHANNEL = re.compile(r"/(?P<channel>[A-Za-z0-9_-]+)/?$")
_KICK_CLIP = re.compile(
    r"/(?P<channel>[A-Za-z0-9_-]+)/clips/(?P<id>clip_[A-Za-z0-9]+)/?$",
    re.IGNORECASE,
)
_TUMBLR_POST = re.compile(r"/[A-Za-z0-9_-]+/(?P<id>[0-9]+)(?:/[^/?#]+)?/?$")
_DIGITS = re.compile(r"[0-9]+$")


def vimeo_url(url: str, parsed: SplitResult) -> str:
    match = _VIMEO_ID.fullmatch(parsed.path)
    return url if match is None else f"https://player.vimeo.com/video/{match.group(1)}"


def douyin_url(url: str, parsed: SplitResult) -> str:
    match = _DOUYIN_VIDEO.fullmatch(parsed.path) or _DOUYIN_SHARE.fullmatch(parsed.path)
    if match is not None:
        return f"https://www.douyin.com/video/{match.group('id')}"
    modal_id = parse_qs(parsed.query).get("modal_id", [])
    if len(modal_id) == 1 and _DIGITS.fullmatch(modal_id[0]):
        return f"https://www.douyin.com/video/{modal_id[0]}"
    return url


def kuaishou_url(url: str, parsed: SplitResult) -> str:
    match = _KUAISHOU_VIDEO.fullmatch(parsed.path)
    return (
        url
        if match is None
        else f"https://v.m.chenzhongtech.com/fw/photo/{match.group('id')}"
    )


def snapchat_url(url: str, parsed: SplitResult) -> str:
    return _require_path(url, parsed, _SNAPCHAT_SPOTLIGHT)


def linkedin_url(_url: str, parsed: SplitResult) -> str:
    if _LINKEDIN_POST.fullmatch(parsed.path) is None:
        raise RunnerFailure("provider_unsupported", status=422)
    query = parse_qs(parsed.query)
    if not set(query) <= {"utm_source", "utm_medium", "utm_campaign"}:
        raise RunnerFailure("provider_unsupported", status=422)
    return f"https://www.linkedin.com{parsed.path}"


def telegram_url(url: str, parsed: SplitResult) -> str:
    return _require_path(
        url,
        parsed,
        _TELEGRAM_POST,
        allowed_queries=frozenset({"", "single"}),
    )


def kick_url(url: str, parsed: SplitResult) -> str:
    clip_match = _KICK_CLIP.fullmatch(parsed.path)
    if clip_match is not None and not parsed.query:
        return url
    channel_match = _KICK_CHANNEL.fullmatch(parsed.path)
    query = parse_qs(parsed.query)
    clip_ids = query.get("clip", [])
    if (
        channel_match is None
        or set(query) != {"clip"}
        or len(clip_ids) != 1
        or re.fullmatch(r"clip_[A-Za-z0-9]+", clip_ids[0], re.IGNORECASE) is None
    ):
        raise RunnerFailure("provider_unsupported", status=422)
    return f"https://kick.com/{channel_match.group('channel')}/clips/{clip_ids[0]}"


def tumblr_url(url: str, parsed: SplitResult) -> str:
    return _require_path(url, parsed, _TUMBLR_POST)


def _require_path(
    url: str,
    parsed: SplitResult,
    pattern: re.Pattern[str],
    *,
    allowed_queries: frozenset[str] = frozenset({""}),
) -> str:
    if pattern.fullmatch(parsed.path) is None or parsed.query not in allowed_queries:
        raise RunnerFailure("provider_unsupported", status=422)
    return url
