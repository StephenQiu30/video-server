"""Structured stdlib logging with URL and secret redaction."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from .security import redact_url, redact_value

SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "secret_key",
    "session_secret",
    "token",
}
STANDARD_LOG_RECORD_KEYS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


def _safe_value(key: str, value: Any) -> Any:
    normalized = key.lower()
    if normalized in SENSITIVE_KEYS or normalized.endswith("_secret"):
        return redact_value(value)
    if normalized.endswith("url") or normalized == "url":
        return redact_url(str(value))
    if isinstance(value, dict):
        return {str(k): _safe_value(str(k), v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(key, item) for item in value]
    return value


class RedactedJsonFormatter(logging.Formatter):
    """Emit one JSON object per line without credentials or URL queries."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in STANDARD_LOG_RECORD_KEYS:
                continue
            payload[key] = _safe_value(key, value)
        if record.exc_info:
            # Tracebacks can contain source URLs, credentials or local paths;
            # keep only the exception class in structured logs.
            exception_type = record.exc_info[0]
            payload["exception_type"] = (
                exception_type.__name__ if exception_type is not None else "unknown"
            )
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure a single redacting handler; safe to call repeatedly."""

    root = logging.getLogger()
    root.setLevel(level.upper())
    handler = root.handlers[0] if root.handlers else logging.StreamHandler()
    handler.setFormatter(RedactedJsonFormatter())
    if not root.handlers:
        root.addHandler(handler)
    for extra in root.handlers[1:]:
        root.removeHandler(extra)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
