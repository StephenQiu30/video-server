"""Safe classifications for bounded multi-asset source discovery."""

from enum import StrEnum


class DiscoveryStatus(StrEnum):
    READY = "ready"
    EMPTY = "empty"


class DiscoveryItemKind(StrEnum):
    OFFICIAL_ACCOUNT_NATIVE = "official_account_native"
    TENCENT_VIDEO = "tencent_video"
    WECHAT_CHANNELS = "wechat_channels"
    UNKNOWN = "unknown"


class DiscoveryDecisionHint(StrEnum):
    CANDIDATE = "candidate"
    EXPORT_REQUIRED = "export_required"
    UNSUPPORTED = "unsupported"


class DiscoveryItemStatus(StrEnum):
    READY = "ready"
    IDENTITY_UNVERIFIED = "identity_unverified"
