"""Compatibility entry point for media URL policy."""

from src.media.url_policy import (
    URLPolicy,
    UrlPolicyError,
    ValidatedUrl,
    assert_safe_url,
    validate_url,
)

__all__ = [
    "URLPolicy",
    "UrlPolicyError",
    "ValidatedUrl",
    "assert_safe_url",
    "validate_url",
]
