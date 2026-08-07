from __future__ import annotations

import re
from urllib.parse import SplitResult, parse_qs, urlsplit

_VIMEO_ID = re.compile(r"/([0-9]+)/?")
_DOUYIN_VIDEO_PATH = re.compile(r"/video/(?P<id>[0-9]+)/?$")
_DOUYIN_SHARE_PATH = re.compile(r"/share/video/(?P<id>[0-9]+)/?$")
_DOUYIN_HOSTS = {
    "douyin.com",
    "www.douyin.com",
    "m.douyin.com",
    "v.douyin.com",
    "iesdouyin.com",
    "www.iesdouyin.com",
}


def provider_request_url(url: str) -> str:
    """Use a provider's canonical endpoint when a shared page is not extractable."""
    parsed = urlsplit(url)
    if parsed.hostname not in {"vimeo.com", "www.vimeo.com"}:
        return _douyin_request_url(url, parsed)
    match = _VIMEO_ID.fullmatch(parsed.path)
    if match is None:
        return url
    return f"https://player.vimeo.com/video/{match.group(1)}"


def _douyin_request_url(url: str, parsed: SplitResult) -> str:
    hostname = parsed.hostname
    if hostname not in _DOUYIN_HOSTS:
        return url

    path = parsed.path
    match = _DOUYIN_VIDEO_PATH.fullmatch(path) or _DOUYIN_SHARE_PATH.fullmatch(path)
    if match is None:
        modal_id = parse_qs(parsed.query).get("modal_id", [])
        if len(modal_id) == 1 and re.fullmatch(r"[0-9]+", modal_id[0]):
            return f"https://www.douyin.com/video/{modal_id[0]}"
        return url
    return f"https://www.douyin.com/video/{match.group('id')}"


def provider_command_args(url: str) -> tuple[str, ...]:
    """Apply request impersonation only to providers that actively require it."""
    hostname = urlsplit(url).hostname
    if hostname in {
        "tiktok.com",
        "www.tiktok.com",
        "m.tiktok.com",
        *_DOUYIN_HOSTS,
    }:
        return ("--impersonate", "Chrome-136:Macos-15")
    return ()


def provider_inspection_attempts(url: str) -> int:
    hostname = urlsplit(url).hostname
    return (
        8
        if hostname
        in {
            "tiktok.com",
            "www.tiktok.com",
            "m.tiktok.com",
            *_DOUYIN_HOSTS,
        }
        else 2
    )


def provider_inspection_retry_delay(url: str) -> float:
    hostname = urlsplit(url).hostname
    return (
        0.5
        if hostname
        in {
            "tiktok.com",
            "www.tiktok.com",
            "m.tiktok.com",
            *_DOUYIN_HOSTS,
        }
        else 1
    )
