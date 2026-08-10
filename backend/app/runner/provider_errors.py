"""Stable yt-dlp failure classification shared by inspect and download."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


def classify_provider_failure(
    command: Sequence[str], stderr: bytes
) -> tuple[str, int] | None:
    if not _is_ytdlp(command):
        return None
    text = stderr.lower()
    command_text = " ".join(command).casefold()
    if _unsupported_provider(command_text, text):
        return "provider_unsupported", 422
    if _unavailable_share_link(command_text, text):
        return "provider_link_unavailable", 422
    if _any(text, b"only drm protected formats", b"this video is drm protected"):
        return "drm_protected", 422
    if _any(text, b"private video", b"this video is private"):
        return "content_private", 403
    if _any(
        text,
        b"members-only content",
        b"join this channel",
        b"premium-only",
        b"subscriber-only",
        b"not entitled",
    ):
        return "content_not_entitled", 403
    if _any(
        text,
        b"account cookies are no longer valid",
        b"cookies have been rotated",
        b"cookie is no longer valid",
    ):
        return "credential_expired", 422
    if _all(text, b"sign in to confirm", b"not a bot"):
        return "egress_challenged", 422
    if _any(text, b"http error 429", b"too many requests", b"rate limit exceeded"):
        return "provider_rate_limited", 429
    if _any(
        text,
        b"not available in your country",
        b"not available in your region",
        b"geo restricted",
    ):
        return "provider_geo_restricted", 422
    if b"po token" in text:
        if _any(text, b"provider unavailable", b"provider failed", b"timed out"):
            return "pot_provider_unavailable", 503
        if _any(text, b"invalid", b"rejected", b"http error 403"):
            return "pot_rejected", 422
        if _any(text, b"required", b"was not provided", b"missing"):
            return "pot_required", 422
    requires_fresh_cookies = b"fresh cookies" in text and b"needed" in text
    requires_vimeo_login = b"vimeo extractor only works when logged-in" in text
    if requires_fresh_cookies or requires_vimeo_login:
        return "credential_required", 422
    if _any(text, b"unable to extract", b"expected one video in the playlist"):
        return "extractor_regression", 502
    return None


def _is_ytdlp(command: Sequence[str]) -> bool:
    return bool(command) and Path(command[0]).name.casefold() in {
        "yt-dlp",
        "yt-dlp.exe",
    }


def _unavailable_share_link(command: str, stderr: bytes) -> bool:
    unavailable = b"unsupported url:" in stderr
    missing_state = b"unable to extract initial state" in stderr
    if not unavailable and not missing_state:
        return False
    return any(
        host in command
        for host in ("douyin.com", "iesdouyin.com", "xiaohongshu.com", "xhslink.com")
    )


def _unsupported_provider(command: str, stderr: bytes) -> bool:
    if b"unsupported url:" not in stderr:
        return False
    return any(
        host in command for host in ("channels.weixin.qq.com", "weixin.qq.com/sph/")
    )


def _any(value: bytes, *markers: bytes) -> bool:
    return any(marker in value for marker in markers)


def _all(value: bytes, *markers: bytes) -> bool:
    return all(marker in value for marker in markers)
