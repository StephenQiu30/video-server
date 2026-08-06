from __future__ import annotations

import hashlib
import hmac
import json


class HmacRequestFingerprinter:
    def __init__(self, key: bytes) -> None:
        if len(key) < 16:
            raise ValueError("fingerprint key must contain at least 16 bytes")
        self._key = key

    def fingerprint(self, namespace: str, *values: str) -> str:
        payload = json.dumps(
            [namespace, *values],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode()
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()
