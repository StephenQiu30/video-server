from typing import Any


def failure_response(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }
