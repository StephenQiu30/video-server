import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

from app.utils.sanitize import redact_url

_URL_PATTERN = re.compile(r"https?://[^\s]+")
_SENSITIVE_KV_PATTERN = re.compile(
    r"(?i)\b(token|cookie|password|authorization|secret|key|access_token|session)\s*[=:]\s*\S+"
)


def _redact_message(message: str) -> str:
    """Redact sensitive information from a log message.

    1. Sanitize URLs found in the message using redact_url().
    2. Replace sensitive key=value / key: value patterns with key=[REDACTED].
    """
    result = _URL_PATTERN.sub(lambda m: redact_url(m.group(0)), message)
    result = _SENSITIVE_KV_PATTERN.sub(lambda m: m.group(0).split("=")[0].split(":")[0] + "=[REDACTED]", result)
    return result


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": _redact_message(record.getMessage()),
            "logger": record.name,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(app_env: str = "local") -> None:
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    handler = logging.StreamHandler(sys.stdout)
    
    if app_env == "production":
        handler.setFormatter(JSONFormatter())
    else:
        # Simple format for local
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO if app_env == "production" else logging.DEBUG)
    
    # Silence some noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
