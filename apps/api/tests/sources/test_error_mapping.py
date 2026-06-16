from app.core.errors import ErrorCode
from app.sources.adapters.ytdlp import YtDlpAdapter


ERROR_CASES = [
    ("need to login with this account", ErrorCode.PLATFORM_RESTRICTED),
    ("members-only content", ErrorCode.PLATFORM_RESTRICTED),
    ("this video is private", ErrorCode.PLATFORM_RESTRICTED),
    ("premium content", ErrorCode.PLATFORM_RESTRICTED),
    ("drm protected", ErrorCode.PLATFORM_RESTRICTED),
    ("geo restricted", ErrorCode.PLATFORM_RESTRICTED),
    ("429 too many requests", ErrorCode.PLATFORM_RATE_LIMITED),
    ("rate limit exceeded", ErrorCode.PLATFORM_RATE_LIMITED),
    ("captcha required", ErrorCode.PLATFORM_RATE_LIMITED),
    ("unsupported url", ErrorCode.UNSUPPORTED_PLATFORM),
    ("no suitable extractor", ErrorCode.UNSUPPORTED_PLATFORM),
    ("no video formats found", ErrorCode.UNSUPPORTED_PLATFORM),
    ("timed out", ErrorCode.PLATFORM_UNAVAILABLE),
    ("connection reset", ErrorCode.PLATFORM_UNAVAILABLE),
    ("some random error", ErrorCode.PARSE_FAILED),
]


class TestYtDlpErrorMapping:
    def test_error_cases(self) -> None:
        adapter = YtDlpAdapter()
        for message, expected_code in ERROR_CASES:
            err = adapter.map_error(RuntimeError(message))
            assert err.code == expected_code, (
                f"Expected {expected_code} for '{message}', got {err.code}"
            )
