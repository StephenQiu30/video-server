"""Application adapters for URL validation and encrypted persistence."""

from __future__ import annotations

import base64
import hmac
import secrets

from app.application.downloads import EncryptedUrl
from app.application.public_input import extract_public_url
from app.core.url_cipher import URLCipher
from app.domain.identifiers import UrlEncryptionKeyId
from app.runner.url_policy import validate_media_url


class MediaUrlValidator:
    def validate(self, url: str) -> str:
        return validate_media_url(extract_public_url(url)).value


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
        if envelope.key_id not in {
            self._key_id,
            UrlEncryptionKeyId.LEGACY_FERNET,
        }:
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
