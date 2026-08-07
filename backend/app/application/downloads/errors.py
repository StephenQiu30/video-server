from __future__ import annotations

from enum import StrEnum


class ApplicationErrorCode(StrEnum):
    DOWNLOAD_NOT_READY = "download_not_ready"
    DURATION_LIMIT_EXCEEDED = "duration_limit_exceeded"
    FORMAT_UNAVAILABLE = "format_unavailable"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    INSPECTION_FAILED = "inspection_failed"
    INSPECTION_TIMEOUT = "inspection_timeout"
    INTERNAL_ERROR = "internal_error"
    INVALID_REQUEST = "invalid_request"
    INVALID_STATE = "invalid_state"
    INVALID_URL = "invalid_url"
    NOT_FOUND = "not_found"
    PROVIDER_ACCESS_REQUIRED = "provider_access_required"
    PROVIDER_LINK_UNAVAILABLE = "provider_link_unavailable"
    RESOURCE_EXPIRED = "resource_expired"


class ApplicationError(RuntimeError):
    def __init__(self, code: ApplicationErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class PersistenceIdempotencyConflict(RuntimeError):
    """A persistence adapter observed an idempotency fingerprint mismatch."""


class PersistenceNotFound(RuntimeError):
    """A persistence adapter could not find an aggregate."""


class PersistenceConflict(RuntimeError):
    """A persistence adapter lost an atomic state precondition race."""


class MediaInspectionFailure(RuntimeError):
    """The runner could not return a valid inspection."""


class MediaInspectionAccessRequired(MediaInspectionFailure):
    """The provider requires a browser session that this service does not accept."""


class MediaInspectionLinkUnavailable(MediaInspectionFailure):
    """The submitted provider link no longer resolves to playable media."""


class MediaInspectionTimeout(MediaInspectionFailure):
    """The runner exceeded the bounded inspection deadline."""
