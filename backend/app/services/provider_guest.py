"""Deployment-owned guest scope; it never names an account or a browser profile."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from app.services.provider_types import ProviderKey

GuestState = Literal[
    "absent", "preparing", "ready", "refreshing", "cooling", "expired", "revoked"
]


@dataclass(frozen=True, slots=True)
class GuestScope:
    provider: ProviderKey
    profile_version: str
    client_profile_id: str
    egress_affinity_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.provider, ProviderKey):
            raise ValueError("guest provider must be registered")
        for value in (
            self.profile_version,
            self.client_profile_id,
            self.egress_affinity_id,
        ):
            if (
                not value
                or len(value) > 128
                or value != value.strip()
                or any(ord(char) < 32 for char in value)
            ):
                raise ValueError("invalid guest scope")

    @property
    def key(self) -> str:
        document = json.dumps(
            [
                "guest",
                self.provider.value,
                self.profile_version,
                self.client_profile_id,
                self.egress_affinity_id,
            ],
            separators=(",", ":"),
        )
        return hashlib.sha256(document.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class GuestContext:
    scope: GuestScope
    state: GuestState
    revision: int
    fence: int
    ciphertext: bytes | None = field(repr=False)
    valid_until: datetime | None
    refresh_after: datetime | None
    retry_at: datetime | None
    reason_code: str | None

    def usable(self, now: datetime) -> bool:
        return (
            self.state != "revoked"
            and self.ciphertext is not None
            and self.valid_until is not None
            and now < self.valid_until
        )


@dataclass(frozen=True, slots=True)
class GuestMaintenanceLease:
    scope: GuestScope
    owner: str
    fence: int
    revision: int
    deadline: datetime
