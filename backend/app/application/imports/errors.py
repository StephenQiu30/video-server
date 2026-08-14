from __future__ import annotations

from enum import StrEnum


class ImportApplicationErrorCode(StrEnum):
    DISABLED = "import_disabled"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    INTERNAL_ERROR = "internal_error"
    INVALID_REQUEST = "invalid_request"
    INVALID_STATE = "invalid_state"
    NOT_FOUND = "not_found"
    SIZE_MISMATCH = "import_size_mismatch"
    STORAGE_UNAVAILABLE = "import_storage_unavailable"
    UPLOAD_INCOMPLETE = "upload_incomplete"
    UPLOAD_SESSION_EXPIRED = "upload_session_expired"


class ImportApplicationError(RuntimeError):
    def __init__(self, code: ImportApplicationErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class ImportPersistenceError(RuntimeError):
    """Base error for an import persistence adapter failure."""


class ImportPersistenceConflict(ImportPersistenceError):
    """An atomic import state precondition was lost."""


class ImportPersistenceIdempotencyConflict(ImportPersistenceError):
    """An idempotency key was reused for a different import."""


class ImportPersistenceNotFound(ImportPersistenceError):
    """The owned import resource does not exist."""


class ImportObjectStorageError(RuntimeError):
    """The import object store is unavailable."""


class MultipartUploadNotFound(ImportObjectStorageError):
    """The object store no longer has the selected multipart upload."""


class MultipartUploadRejected(ImportObjectStorageError):
    """The object store rejected the submitted part manifest."""
