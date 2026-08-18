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
    if _unsupported_media(command_text, text):
        return "provider_media_unsupported", 422
    if _unavailable_youtube_video(command_text, text):
        return "provider_link_unavailable", 422
    if _unavailable_share_link(command_text, text):
        return "provider_link_unavailable", 422
    if _any(
        text,
        b"only drm protected formats",
        b"this video is drm protected",
        b"this format is drm protected",
    ):
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
        # The same YouTube message has two materially different meanings. An
        # anonymous request is an exit reputation challenge, while a request
        # that already supplied an operator cookie jar means that session no
        # longer authenticates. Keep those diagnoses distinct so operations
        # can rotate the session instead of repeatedly retrying the egress.
        if "--cookies" in command:
            return "credential_expired", 422
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
    requires_account = _any(
        text,
        b"account authentication is required",
        b"rate-limit reached or login required",
        b"login required. use --cookies",
    )
    if requires_fresh_cookies or requires_vimeo_login or requires_account:
        return "credential_required", 422
    if "tiktok.com" in command_text and _any(
        text,
        b"unexpected response from webpage request",
        b"unable to extract challenge data",
        b"unable to extract universal data for rehydration",
    ):
        # These responses are TikTok's short-lived JavaScript/WAF challenge,
        # not a malformed media response. Surface the recovery boundary so
        # operations can refresh the browser session instead of retrying the
        # extractor indefinitely.
        return "egress_challenged", 422
    if "facebook.com" in command_text and _any(
        text,
        b"cannot parse data",
        b"facebook post media structure could not be identified",
    ):
        return "extractor_regression", 502
    is_xiaohongshu = any(
        host in command_text for host in ("xiaohongshu.com", "xhslink.com")
    )
    if is_xiaohongshu and _any(
        text,
        b"no video formats found",
        b"xiaohongshu note media structure could not be identified",
    ):
        # The public page may still exist while the extractor's expected
        # noteDetailMap payload has disappeared. This is an integration
        # regression, not an invalid link or something an end user can fix.
        return "extractor_regression", 502
    if _any(
        text,
        b"unable to extract",
        b"expected one video in the playlist",
        b"unexpected response from webpage request",
        b"universal data for rehydration",
    ):
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
    kuaishou_unavailable = b"kuaishou public link unavailable" in stderr
    if not unavailable and not missing_state and not kuaishou_unavailable:
        return False
    return any(
        host in command
        for host in (
            "douyin.com",
            "iesdouyin.com",
            "xiaohongshu.com",
            "xhslink.com",
            "kuaishou.com",
            "kuaishou.cn",
            "chenzhongtech.com",
            "gifshow.com",
        )
    )


def _unavailable_youtube_video(command: str, stderr: bytes) -> bool:
    if not any(host in command for host in ("youtube.com", "youtu.be")):
        return False
    return _any(
        stderr,
        b"video unavailable",
        b"this video is unavailable",
        b"video is no longer available",
    )


def _unsupported_provider(command: str, stderr: bytes) -> bool:
    wechat = b"unsupported url:" in stderr and any(
        host in command for host in ("channels.weixin.qq.com", "weixin.qq.com/sph/")
    )
    kuaishou_image = (
        b"kuaishou image posts are not supported by the video runner" in stderr
        and any(
            host in command
            for host in (
                "kuaishou.com",
                "kuaishou.cn",
                "chenzhongtech.com",
                "gifshow.com",
            )
        )
    )
    return wechat or kuaishou_image


def _unsupported_media(command: str, stderr: bytes) -> bool:
    return "facebook.com" in command and (
        b"facebook image and multi-asset posts are not supported" in stderr
    )


def _any(value: bytes, *markers: bytes) -> bool:
    return any(marker in value for marker in markers)


def _all(value: bytes, *markers: bytes) -> bool:
    return all(marker in value for marker in markers)
