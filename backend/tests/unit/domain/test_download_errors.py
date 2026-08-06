from app.domain.downloads import DownloadErrorCode


def test_error_codes_are_stable_snake_case_values() -> None:
    assert {code.value for code in DownloadErrorCode} == {
        "cancelled",
        "download_timeout",
        "format_unavailable",
        "inspection_timeout",
        "internal_error",
        "media_validation_failed",
        "output_limit_exceeded",
        "storage_unavailable",
        "temp_space_exhausted",
        "transcode_required",
        "unsupported_source",
        "worker_lost",
    }


def test_only_transient_errors_are_retryable() -> None:
    assert DownloadErrorCode.STORAGE_UNAVAILABLE.retryable is True
    assert DownloadErrorCode.WORKER_LOST.retryable is True
    assert DownloadErrorCode.DOWNLOAD_TIMEOUT.retryable is True
    assert DownloadErrorCode.FORMAT_UNAVAILABLE.retryable is False
    assert DownloadErrorCode.TRANSCODE_REQUIRED.retryable is False
