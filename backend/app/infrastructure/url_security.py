"""Application adapters for URL validation and encrypted persistence."""

from __future__ import annotations

import base64
import hmac
import re
import secrets

from app.application.downloads import EncryptedUrl
from app.core.url_cipher import URLCipher
from app.runner.url_policy import validate_media_url

_XHS_SHORT_LINK = re.compile(
    r"(?<![A-Za-z0-9.-])(?P<url>(?:https?://)?(?:www\.)?xhslink\.com/"
    r"(?:a|m)/[A-Za-z0-9]+(?:[/?#][^\s]*)?)",
    re.IGNORECASE,
)
_SHARE_TRAILING_PUNCTUATION = ".,;:!?，。；：！？)]}）】》"


class MediaUrlValidator:
    def validate(self, url: str) -> str:
        return validate_media_url(_normalize_public_share_input(url)).value


def _normalize_public_share_input(value: str) -> str:
    """Extract the single known-safe URL form emitted by the XHS share sheet."""
    if not isinstance(value, str):
        return value
    matches = tuple(_XHS_SHORT_LINK.finditer(value))
    if len(matches) != 1:
        return value
    candidate = matches[0].group("url").rstrip(_SHARE_TRAILING_PUNCTUATION)
    if not candidate.lower().startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    return candidate


class FernetUrlEnvelope:
    """Bind a random nonce and key id to each encrypted source URL."""

    def __init__(self, cipher: URLCipher, *, key_id: str) -> None:
        if not key_id.strip():
            raise ValueError("URL encryption key id cannot be blank")
        self._cipher = cipher
        self._key_id = key_id

    def encrypt(self, url: str) -> EncryptedUrl:
        nonce = secrets.token_bytes(16)
        prefix = base64.urlsafe_b64encode(nonce).decode()
        ciphertext = self._cipher.encrypt(f"{prefix}:{url}")
        return EncryptedUrl(
            ciphertext=ciphertext,
            nonce=nonce,
            key_id=self._key_id,
        )

    def decrypt(self, envelope: EncryptedUrl) -> str:
        if envelope.key_id != self._key_id:
            raise ValueError("unknown URL encryption key id")
        value = self._cipher.decrypt(envelope.ciphertext)
        try:
            encoded_nonce, url = value.split(":", maxsplit=1)
            embedded_nonce = base64.b64decode(
                encoded_nonce,
                altchars=b"-_",
                validate=True,
            )
        except (ValueError, UnicodeEncodeError) as exc:
            raise ValueError("invalid encrypted URL envelope") from exc
        if not hmac.compare_digest(embedded_nonce, envelope.nonce):
            raise ValueError("encrypted URL nonce does not match")
        return url
