from __future__ import annotations

import json
import logging

from src.core.logging import RedactedJsonFormatter, configure_logging


def test_formatter_redacts_secret_and_url_query() -> None:
    record = logging.LogRecord(
        name="video.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request completed",
        args=(),
        exc_info=None,
    )
    record.secret = "top-secret"  # type: ignore[attr-defined]
    record.url = "https://example.test/video?id=secret"  # type: ignore[attr-defined]

    payload = json.loads(RedactedJsonFormatter().format(record))

    assert "top-secret" not in json.dumps(payload)
    assert "?" not in payload["url"]


def test_configure_logging_is_idempotent() -> None:
    configure_logging("INFO")
    configure_logging("INFO")

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert root.level == logging.INFO
