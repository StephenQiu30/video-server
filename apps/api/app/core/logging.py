import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Redaction logic for sensitive fields
        message = log_data["message"]
        sensitive_keywords = ["token", "cookie", "password", "authorization", "secret", "key"]
        for keyword in sensitive_keywords:
            if keyword in message.lower():
                log_data["message"] = "[REDACTED]"
                break
        
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
