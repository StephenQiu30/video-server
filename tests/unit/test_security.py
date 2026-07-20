from __future__ import annotations

from src.core.security import redact_url, redact_value


def test_redact_url_removes_credentials_query_and_fragment() -> None:
    value = "https://user:password@example.test/media.mp4?token=secret#fragment"

    assert redact_url(value) == "https://example.test/media.mp4"


def test_redact_value_never_returns_secret() -> None:
    assert redact_value("super-secret") == "***"
    assert redact_value("") == "***"
