"""Canonical handling for user-provided public media input."""

from __future__ import annotations

import re

_XHS_SHORT_LINK = re.compile(
    r"(?<![A-Za-z0-9.-])(?P<url>(?:https?://)?(?:www\.)?xhslink\.com/"
    r"(?:a|m)/[A-Za-z0-9]+(?:[/?#][^\s]*)?)",
    re.IGNORECASE,
)
_HTTP_URL = re.compile(
    r"https?://[^\s，。；：！？、）》）】]+",
    re.IGNORECASE,
)
_SHARE_TRAILING_PUNCTUATION = ".,;:!?，。；：！？)]}）】》"


def extract_public_url(value: str) -> str:
    """Extract the sole public URL from a direct URL or share message.

    This is the application boundary for public-input parsing. Clients send
    the original pasted value; provider adapters only receive the canonical
    URL returned by this function after URL policy validation.
    """
    if not isinstance(value, str):
        return value
    public_urls = tuple(match.group() for match in _HTTP_URL.finditer(value))
    if len(public_urls) > 1:
        return value
    if len(public_urls) == 1:
        return public_urls[0].rstrip(_SHARE_TRAILING_PUNCTUATION)
    matches = tuple(_XHS_SHORT_LINK.finditer(value))
    if len(matches) != 1:
        return value
    candidate = matches[0].group("url").rstrip(_SHARE_TRAILING_PUNCTUATION)
    if not candidate.lower().startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    return candidate
