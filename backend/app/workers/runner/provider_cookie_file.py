"""Read a deployment-owned, provider-scoped Cookie file without a desktop agent."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from app.services.provider_types import ProviderKey, ProviderSessionVersion
from app.workers.runner._secure_file import no_follow_flag
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.netscape_cookie import live_cookie_payload
from app.workers.runner.provider_cookie_lease import MAX_COOKIE_BYTES
from app.workers.runner.provider_session_policy import (
    ProviderSessionSource,
    browser_session_policy,
)


class ProviderCookieFile:
    """Reopen the read-only source for every operation; never write session updates."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self, provider: ProviderKey, version: ProviderSessionVersion) -> bytes:
        policy = browser_session_policy(provider)
        if (
            version is not policy.version
            or policy.source is ProviderSessionSource.MANAGED_YUANBAO
        ):
            raise RunnerFailure("provider_session_not_allowed", status=422)
        try:
            descriptor = os.open(
                self._path,
                os.O_RDONLY | os.O_NONBLOCK | no_follow_flag(),
            )
            with os.fdopen(descriptor, "rb") as source:
                info = os.fstat(source.fileno())
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or info.st_mode & 0o007
                    or not 0 < info.st_size <= MAX_COOKIE_BYTES
                ):
                    raise RunnerFailure("credential_rejected", status=422)
                payload = source.read(MAX_COOKIE_BYTES + 1)
        except FileNotFoundError as exc:
            raise RunnerFailure("credential_required", status=422) from exc
        except OSError as exc:
            raise RunnerFailure("provider_session_unavailable", status=503) from exc
        live, names = live_cookie_payload(payload, frozenset(policy.domains))
        if not policy.accepts(frozenset(names)):
            raise RunnerFailure("credential_expired", status=422)
        return live

    async def is_ready(
        self, provider: ProviderKey, version: ProviderSessionVersion
    ) -> bool:
        try:
            self.read(provider, version)
        except RunnerFailure:
            return False
        return True

    async def sync(
        self, provider: ProviderKey, version: ProviderSessionVersion
    ) -> bytes:
        return self.read(provider, version)
