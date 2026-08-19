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
    PROVIDER_AUTH_REQUIRED = "provider_auth_required"
    PROVIDER_SESSION_EXPIRED = "provider_session_expired"
    PROVIDER_VERIFICATION_FAILED = "provider_verification_failed"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_GEO_RESTRICTED = "provider_geo_restricted"
    PROVIDER_CONTENT_RESTRICTED = "provider_content_restricted"
    PROVIDER_DRM_PROTECTED = "provider_drm_protected"
    PROVIDER_TEMPORARILY_UNAVAILABLE = "provider_temporarily_unavailable"
    PROVIDER_LINK_UNAVAILABLE = "provider_link_unavailable"
    PROVIDER_MEDIA_UNSUPPORTED = "provider_media_unsupported"
    PROVIDER_UNSUPPORTED = "provider_unsupported"
    RESOURCE_EXPIRED = "resource_expired"
    STORAGE_UNAVAILABLE = "storage_unavailable"


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


class MediaInspectionDurationLimitExceeded(MediaInspectionFailure):
    """The media exceeds the configured duration safety boundary."""


class MediaInspectionAuthRequired(MediaInspectionFailure):
    """The provider requires an approved session."""


class MediaInspectionSessionExpired(MediaInspectionFailure):
    """The selected provider session is no longer usable."""


class MediaInspectionVerificationFailed(MediaInspectionFailure):
    """Provider request proof, script challenge, or egress verification failed."""


class MediaInspectionRateLimited(MediaInspectionFailure):
    """The provider rejected the bounded request rate."""


class MediaInspectionGeoRestricted(MediaInspectionFailure):
    """The content is unavailable in the configured region."""


class MediaInspectionContentRestricted(MediaInspectionFailure):
    """The content is private or requires an entitlement."""


class MediaInspectionDrmProtected(MediaInspectionFailure):
    """The content is DRM protected and outside the product boundary."""


class MediaInspectionTemporarilyUnavailable(MediaInspectionFailure):
    """The provider adapter or attestation service is degraded."""


class MediaInspectionLinkUnavailable(MediaInspectionFailure):
    """The submitted provider link no longer resolves to playable media."""


class MediaInspectionMediaUnsupported(MediaInspectionFailure):
    """The submitted provider item is not a supported single video."""


class MediaInspectionFormatUnavailable(MediaInspectionFailure):
    """The media resolved but offers no supported semantic download format."""


class MediaInspectionUnsupported(MediaInspectionFailure):
    """The provider is outside the capabilities of the secure runner."""


class MediaInspectionTimeout(MediaInspectionFailure):
    """The runner exceeded the bounded inspection deadline."""
