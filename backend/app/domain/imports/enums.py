from __future__ import annotations

from enum import StrEnum


class ContentKind(StrEnum):
    VIDEO = "video"
    SCREENPLAY = "screenplay"


class ImportStatus(StrEnum):
    UPLOADING = "uploading"
    VERIFYING = "verifying"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ImportErrorCode(StrEnum):
    UPLOAD_SESSION_EXPIRED = "upload_session_expired"
    UPLOAD_INCOMPLETE = "upload_incomplete"
    SIZE_MISMATCH = "import_size_mismatch"
    SHA256_MISMATCH = "import_sha256_mismatch"
    VIDEO_INVALID = "video_import_invalid"
    DOCUMENT_FORMAT_UNSUPPORTED = "document_format_unsupported"
    DOCUMENT_ENCRYPTED = "document_encrypted"
    DOCUMENT_ARCHIVE_UNSAFE = "document_archive_unsafe"
    DOCUMENT_TEXT_UNAVAILABLE = "document_text_unavailable"
    DOCUMENT_STRUCTURE_INVALID = "document_structure_invalid"
