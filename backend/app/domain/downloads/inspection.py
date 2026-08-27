"""Stable inspection decisions shared by API and execution boundaries."""

from enum import StrEnum


class SourceOrigin(StrEnum):
    PUBLIC_URL = "public_url"
    DISCOVERED_ITEM = "discovered_item"
    OFFICIAL_ASSET = "official_asset"
    VERIFIED_IMPORT = "verified_import"


class ExecutionMode(StrEnum):
    PROVIDER_RUNNER = "provider_runner"
    ARTICLE_NATIVE = "article_native"
    OFFICIAL_CONNECTOR = "official_connector"
    VERIFIED_IMPORT = "verified_import"


class AccessDecision(StrEnum):
    DOWNLOADABLE = "downloadable"
    PLAYBACK_ONLY = "playback_only"
    EXPORT_REQUIRED = "export_required"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"


class EntitlementState(StrEnum):
    PUBLIC_FREE = "public_free"
    OFFICIAL_DOWNLOAD_GRANT = "official_download_grant"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class IdentityState(StrEnum):
    VERIFIED = "verified"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


class ProtectionState(StrEnum):
    CLEAR = "clear"
    ENCRYPTED = "encrypted"
    DRM = "drm"
    UNKNOWN = "unknown"


class RightsBasis(StrEnum):
    PUBLIC_ACCESS = "public_access"
    OWNER_AUTHORIZED_EXPORT = "owner_authorized_export"
    OFFICIAL_ASSET_GRANT = "official_asset_grant"
    USER_PROVIDED = "user_provided"
