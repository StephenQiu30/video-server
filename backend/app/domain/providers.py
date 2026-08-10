"""Provider capability and non-secret access context primitives."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Self

_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


class ProviderAccessMode(StrEnum):
    ANONYMOUS = "anonymous"
    OPERATOR_MANAGED = "operator_managed"


class ProviderCapability(StrEnum):
    SINGLE_VIDEO = "single_video"
    SHORT_VIDEO = "short_video"
    CLIP_OR_VOD = "clip_or_vod"
    AUDIO_VIDEO_SPLIT = "audio_video_split"
    SUBTITLES = "subtitles"
    IMAGE_OR_CAROUSEL = "image_or_carousel"
    LIVE = "live"
    PLAYLIST = "playlist"


class ProviderSupportStatus(StrEnum):
    UNKNOWN = "unknown"
    VERIFIED = "verified"
    DEGRADED = "degraded"
    ACCESS_REQUIRED = "access_required"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"
    DISABLED = "disabled"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class ProviderAccessContextRef:
    """Immutable references needed to reproduce provider access safely."""

    provider_key: str
    profile_version: str
    access_mode: ProviderAccessMode
    credential_version_id: str | None
    egress_affinity_id: str
    client_profile_id: str
    attestation_provider_version: str | None
    engine_commit: str

    def __post_init__(self) -> None:
        values = (
            self.provider_key,
            self.profile_version,
            self.egress_affinity_id,
            self.client_profile_id,
            self.engine_commit,
        )
        optional = (self.credential_version_id, self.attestation_provider_version)
        if any(_REFERENCE.fullmatch(value) is None for value in values):
            raise ValueError("provider access context contains an invalid reference")
        if any(
            value is not None and _REFERENCE.fullmatch(value) is None
            for value in optional
        ):
            raise ValueError("provider access context contains an invalid reference")
        has_credential = self.credential_version_id is not None
        if has_credential != (self.access_mode is ProviderAccessMode.OPERATOR_MANAGED):
            raise ValueError("provider credential reference does not match access mode")

    def to_document(self) -> dict[str, str | None]:
        return {
            "provider_key": self.provider_key,
            "profile_version": self.profile_version,
            "access_mode": self.access_mode.value,
            "credential_version_id": self.credential_version_id,
            "egress_affinity_id": self.egress_affinity_id,
            "client_profile_id": self.client_profile_id,
            "attestation_provider_version": self.attestation_provider_version,
            "engine_commit": self.engine_commit,
        }

    @classmethod
    def from_document(cls, value: object) -> Self:
        if not isinstance(value, dict):
            raise ValueError("provider access context must be an object")
        keys = {
            "provider_key",
            "profile_version",
            "access_mode",
            "credential_version_id",
            "egress_affinity_id",
            "client_profile_id",
            "attestation_provider_version",
            "engine_commit",
        }
        if set(value) != keys:
            raise ValueError("provider access context fields are invalid")

        def required(name: str) -> str:
            item = value[name]
            if not isinstance(item, str):
                raise ValueError("provider access context field is invalid")
            return item

        def optional(name: str) -> str | None:
            item = value[name]
            if item is not None and not isinstance(item, str):
                raise ValueError("provider access context field is invalid")
            return item

        return cls(
            provider_key=required("provider_key"),
            profile_version=required("profile_version"),
            access_mode=ProviderAccessMode(required("access_mode")),
            credential_version_id=optional("credential_version_id"),
            egress_affinity_id=required("egress_affinity_id"),
            client_profile_id=required("client_profile_id"),
            attestation_provider_version=optional("attestation_provider_version"),
            engine_commit=required("engine_commit"),
        )
