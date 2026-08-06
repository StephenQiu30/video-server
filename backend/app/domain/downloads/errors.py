from __future__ import annotations

from app.domain.downloads.enums import DownloadErrorCode


class FormatSelectionError(ValueError):
    def __init__(self, code: DownloadErrorCode) -> None:
        if code not in {
            DownloadErrorCode.FORMAT_UNAVAILABLE,
            DownloadErrorCode.TRANSCODE_REQUIRED,
        }:
            raise ValueError("invalid format selection error code")
        self.code = code
        super().__init__(code.value)


class InvalidJobTransition(ValueError):
    """Raised when a command violates the download job state contract."""
