from unittest.mock import patch

import pytest
from src.media.url_policy import UrlPolicyError, validate_url


@pytest.mark.parametrize(
    "value",
    [
        "ftp://example.com/video",
        "http://user:secret@example.com/video",
        "http://example.com:8080/video",
        "http://127.0.0.1/video",
        "https://example.com/video#fragment",
        "https://example.com/a\nheader",
    ],
)
def test_url_policy_rejects_unsafe_values(value: str) -> None:
    with pytest.raises(UrlPolicyError):
        validate_url(value, resolve=False)


def test_url_policy_rejects_private_dns_answers() -> None:
    with patch(
        "src.media.url_policy.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("10.0.0.4", 80))],
    ):
        with pytest.raises(UrlPolicyError):
            validate_url("https://example.com/video")


def test_url_policy_canonicalizes_scheme_and_path() -> None:
    with patch(
        "src.media.url_policy.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
    ):
        value = validate_url("HTTPS://Example.com", resolve=True)
    assert value.value == "https://Example.com/"
    assert value.host == "example.com"
