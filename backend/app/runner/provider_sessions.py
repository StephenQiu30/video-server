"""Operator-managed provider session isolation for the media runner."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from app.domain.providers import (
    ProviderAccessContextRef,
    ProviderAccessMode,
    ProviderKey,
    ProviderSessionVersion,
)
from app.runner.errors import RunnerFailure
from app.runner.provider_cookie_sync import (
    ProviderCookieSync,
    ProviderCookieSyncClient,
)
from app.runner.provider_registry import ProviderProfile, provider_profile
from app.runner.provider_session_files import (
    operation_cookie,
    prepare_private_root,
    require_memory_backed_root,
    validated_cookie_payload,
)
from app.runner.settings import RunnerSettings


class ProviderSessionStore:
    """Validate one-operation Cookie leases and issue tmpfs-backed jars."""

    def __init__(
        self,
        settings: RunnerSettings,
        *,
        cookie_sync: ProviderCookieSync | None = None,
        enforce_memory_backing: bool = True,
    ) -> None:
        self._settings = settings
        self._temp_root = settings.runner_provider_session_temp_root
        self._versions = dict(settings.runner_operator_session_versions)
        self._gate = asyncio.Semaphore(1)
        sync_root = settings.runner_provider_cookie_sync_root
        self._cookie_sync: ProviderCookieSync | None
        if cookie_sync is not None:
            self._cookie_sync = cookie_sync
        elif sync_root is not None:
            self._cookie_sync = ProviderCookieSyncClient(sync_root)
        else:
            self._cookie_sync = None
        if settings.runner_access_mode is ProviderAccessMode.OPERATOR_MANAGED:
            prepare_private_root(self._temp_root)
            if enforce_memory_backing:
                require_memory_backed_root(self._temp_root)

    def is_ready(self) -> bool:
        if self._settings.runner_access_mode is ProviderAccessMode.ANONYMOUS:
            return True
        assert self._cookie_sync is not None
        provider, version = next(iter(self._versions.items()))
        return self._cookie_sync.is_ready(provider, version)

    def context_for(self, source: str | ProviderProfile) -> ProviderAccessContextRef:
        profile = provider_profile(source) if isinstance(source, str) else source
        mode = self._settings.runner_access_mode
        if mode not in profile.access_modes:
            raise RunnerFailure("provider_session_not_allowed", status=422)
        version = (
            self._versions.get(ProviderKey(profile.key))
            if mode is ProviderAccessMode.OPERATOR_MANAGED
            else None
        )
        if mode is ProviderAccessMode.OPERATOR_MANAGED and version is None:
            raise RunnerFailure("credential_required", status=422)
        return ProviderAccessContextRef(
            provider_key=profile.key,
            profile_version=profile.version,
            access_mode=mode,
            credential_version_id=None if version is None else version.value,
            egress_affinity_id=self._settings.egress_affinity_for(profile.key),
            client_profile_id=profile.client_profile_id,
            attestation_provider_version=(
                self._settings.runner_youtube_pot_provider_version
                if profile.key == ProviderKey.YOUTUBE
                and self._settings.runner_youtube_pot_base_url is not None
                else None
            ),
            engine_commit=self._settings.runner_ytdlp_commit,
        )

    def validate_context(
        self,
        source: str | ProviderProfile,
        expected: ProviderAccessContextRef,
    ) -> ProviderAccessContextRef:
        current = self.context_for(source)
        if current.access_mode is ProviderAccessMode.ANONYMOUS:
            if current != expected:
                raise RunnerFailure("client_context_mismatch", status=409)
            return current
        if expected != current:
            raise RunnerFailure("credential_revoked", status=422)
        return current

    @asynccontextmanager
    async def operation(
        self, context: ProviderAccessContextRef
    ) -> AsyncIterator[Path | None]:
        if context.access_mode is ProviderAccessMode.ANONYMOUS:
            yield None
            return
        raw_version = context.credential_version_id
        if raw_version is None:
            raise RunnerFailure("credential_required", status=422)
        try:
            provider = ProviderKey(context.provider_key)
            version = ProviderSessionVersion(raw_version)
        except ValueError as exc:
            raise RunnerFailure("credential_revoked", status=422) from exc
        async with self._gate:
            assert self._cookie_sync is not None
            exported = await self._cookie_sync.sync(provider, version)
            payload = self._validated_payload(provider, exported)
            with operation_cookie(
                payload, self._temp_root, context.provider_key
            ) as jar:
                yield jar

    def _validated_payload(self, provider: ProviderKey, payload: bytes) -> bytes:
        profile = _profile_for_key(provider)
        if ProviderAccessMode.OPERATOR_MANAGED not in profile.access_modes:
            raise RunnerFailure("provider_session_not_allowed", status=422)
        return validated_cookie_payload(
            payload,
            profile.cookie_domain_allowlist,
        )


def _profile_for_key(key: str | ProviderKey) -> ProviderProfile:
    from app.runner.provider_registry import default_provider_registry

    for profile in default_provider_registry().profiles:
        if profile.key == key:
            return profile
    raise RunnerFailure("provider_session_not_allowed", status=422)
