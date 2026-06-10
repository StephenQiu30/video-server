"""Tests for centralized ErrorCode enum and AppError compatibility."""

from app.core.errors import AppError, ErrorCode


def test_error_code_enum_covers_entry_codes() -> None:
    """ErrorCode 枚举必须包含入口校验相关错误码。"""
    assert ErrorCode.INVALID_URL == "invalid_url"
    assert ErrorCode.UNSAFE_URL == "unsafe_url"


def test_error_code_enum_covers_parse_codes() -> None:
    """ErrorCode 枚举必须包含解析相关错误码。"""
    assert ErrorCode.PARSE_FAILED == "parse_failed"
    assert ErrorCode.PLATFORM_RESTRICTED == "platform_restricted"
    assert ErrorCode.PLATFORM_RATE_LIMITED == "platform_rate_limited"
    assert ErrorCode.UNSUPPORTED_PLATFORM == "unsupported_platform"
    assert ErrorCode.PLATFORM_UNAVAILABLE == "platform_unavailable"


def test_error_code_enum_covers_infra_codes() -> None:
    """ErrorCode 枚举必须包含基础设施相关错误码。"""
    assert ErrorCode.ENGINE_UNAVAILABLE == "engine_unavailable"
    assert ErrorCode.QUEUE_UNAVAILABLE == "queue_unavailable"
    assert ErrorCode.STORAGE_UNAVAILABLE == "storage_unavailable"


def test_error_code_enum_covers_auth_codes() -> None:
    """ErrorCode 枚举必须包含认证相关错误码。"""
    assert ErrorCode.INVALID_CREDENTIALS == "invalid_credentials"
    assert ErrorCode.USER_DISABLED == "user_disabled"
    assert ErrorCode.AUTH_LOCKED == "auth_locked"
    assert ErrorCode.REGISTRATION_DISABLED == "registration_disabled"
    assert ErrorCode.REGISTRATION_FAILED == "registration_failed"


def test_error_code_enum_covers_task_codes() -> None:
    """ErrorCode 枚举必须包含任务相关错误码。"""
    assert ErrorCode.INVALID_STATE == "invalid_state"
    assert ErrorCode.LIMIT_EXCEEDED == "limit_exceeded"
    assert ErrorCode.NOT_FOUND == "not_found"
    assert ErrorCode.RETENTION_EXPIRED == "retention_expired"
    assert ErrorCode.RETRY_SUPERSEDED == "retry_superseded"


def test_error_code_enum_covers_general_codes() -> None:
    """ErrorCode 枚举必须包含通用错误码。"""
    assert ErrorCode.RATE_LIMITED == "rate_limited"
    assert ErrorCode.VALIDATION_ERROR == "validation_error"
    assert ErrorCode.INTERNAL_ERROR == "internal_error"


def test_error_code_is_str() -> None:
    """ErrorCode 值应可直接作为字符串使用。"""
    code: str = ErrorCode.INVALID_URL
    assert code == "invalid_url"


def test_app_error_accepts_error_code_enum() -> None:
    """AppError 应接受 ErrorCode 枚举值。"""
    exc = AppError(ErrorCode.INVALID_URL, "请输入视频链接", 422)
    assert exc.code == "invalid_url"
    assert exc.status_code == 422


def test_app_error_accepts_string_for_backward_compat() -> None:
    """AppError 应继续接受字符串以保持向后兼容。"""
    exc = AppError("invalid_url", "请输入视频链接", 422)
    assert exc.code == "invalid_url"
