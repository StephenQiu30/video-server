from __future__ import annotations

import re
from urllib.parse import urlsplit

_VIMEO_ID = re.compile(r"/([0-9]+)/?")


def provider_request_url(url: str) -> str:
    """Use a public player endpoint when a provider's canonical page is broken."""
    parsed = urlsplit(url)
    if parsed.hostname not in {"vimeo.com", "www.vimeo.com"}:
        return url
    match = _VIMEO_ID.fullmatch(parsed.path)
    if match is None:
        return url
    return f"https://player.vimeo.com/video/{match.group(1)}"


def provider_command_args(url: str) -> tuple[str, ...]:
    """Apply request impersonation only to providers that actively require it."""
    hostname = urlsplit(url).hostname
    if hostname in {"tiktok.com", "www.tiktok.com", "m.tiktok.com"}:
        return ("--impersonate", "Chrome-136:Macos-15")
    return ()


def provider_inspection_attempts(url: str) -> int:
    hostname = urlsplit(url).hostname
    return 8 if hostname in {"tiktok.com", "www.tiktok.com", "m.tiktok.com"} else 2


def provider_inspection_retry_delay(url: str) -> float:
    hostname = urlsplit(url).hostname
    return 0.5 if hostname in {"tiktok.com", "www.tiktok.com", "m.tiktok.com"} else 1
