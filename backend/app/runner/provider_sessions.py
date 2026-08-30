"""Operator-managed provider session isolation for the media runner."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path

from app.domain.providers import ProviderAccessContextRef, ProviderAccessMode
from app.runner.errors import RunnerFailure
from app.runner.provider_cookie_sync import (
    ProviderCookieSync,
    ProviderCookieSyncClient,
)
from app.runner.provider_registry import ProviderProfile, provider_profile
from app.runner.provider_session_files import (
    operation_cookie,
    prepare_private_root,
    validated_cookie_payload,
)
from app.runner.settings import RunnerSettings


class ProviderSessionStore:
    """Validate immutable Cookie sources and issue per-operation writable jars."""

    def __init__(
        self,
        settings: RunnerSettings,
        *,
        clock: Callable[[], float] = time.time,
        cookie_sync: ProviderCookieSync | None = None,
    ) -> None:
        self._settings = settings
        self._source_root = settings.runner_provider_secret_root
        self._temp_root = settings.runner_provider_secret_temp_root
        self._versions = dict(settings.runner_operator_session_versions)
        retained = settings.runner_operator_retained_session_versions
        self._accepted_versions = {
            provider: frozenset((*retained.get(provider, ()), version))
            for provider, version in self._versions.items()
        }
        self._clock = clock
        self._gate = asyncio.Semaphore(1)
        sync_root = settings.runner_youtube_cookie_sync_root
        self._cookie_sync: ProviderCookieSync | None
        if cookie_sync is not None:
            self._cookie_sync = cookie_sync
        elif sync_root is not None:
            self._cookie_sync = ProviderCookieSyncClient(sync_root)
        else:
            self._cookie_sync = None
        if settings.runner_access_mode is ProviderAccessMode.OPERATOR_MANAGED:
            prepare_private_root(self._temp_root)

    def is_ready(self) -> bool:
        if self._settings.runner_access_mode is ProviderAccessMode.ANONYMOUS:
            return True
        if self._live_sync_enabled():
            assert self._cookie_sync is not None
            return self._cookie_sync.is_ready()
        try:
            for provider, version in self._versions.items():
                self._validated_payload(provider, version)
        except RunnerFailure:
            return False
        return True

    def context_for(self, source: str | ProviderProfile) -> ProviderAccessContextRef:
        profile = provider_profile(source) if isinstance(source, str) else source
        mode = self._settings.runner_access_mode
        if mode not in profile.access_modes:
            raise RunnerFailure("provider_session_not_allowed", status=422)
        version = (
            self._versions.get(profile.key)
            if mode is ProviderAccessMode.OPERATOR_MANAGED
            else None
        )
        if mode is ProviderAccessMode.OPERATOR_MANAGED and version is None:
            raise RunnerFailure("credential_required", status=422)
        return ProviderAccessContextRef(
            provider_key=profile.key,
            profile_version=profile.version,
            access_mode=mode,
            credential_version_id=version,
            egress_affinity_id=self._settings.egress_affinity_for(profile.key),
            client_profile_id=profile.client_profile_id,
            attestation_provider_version=(
                self._settings.runner_youtube_pot_provider_version
                if profile.key == "youtube"
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
        accepted = self._accepted_versions.get(current.provider_key, frozenset())
        if expected.credential_version_id not in accepted:
            raise RunnerFailure("credential_revoked", status=422)
        retained = replace(
            current,
            credential_version_id=expected.credential_version_id,
        )
        if retained != expected:
            raise RunnerFailure("client_context_mismatch", status=409)
        return retained

    @asynccontextmanager
    async def operation(
        self, context: ProviderAccessContextRef
    ) -> AsyncIterator[Path | None]:
        if context.access_mode is ProviderAccessMode.ANONYMOUS:
            yield None
            return
        version = context.credential_version_id
        if version is None:
            raise RunnerFailure("credential_required", status=422)
        async with self._gate:
            if self._uses_live_sync(context.provider_key, version):
                assert self._cookie_sync is not None
                await self._cookie_sync.sync()
            payload = self._validated_payload(context.provider_key, version)
            with operation_cookie(
                payload, self._temp_root, context.provider_key
            ) as jar:
                yield jar

    def _uses_live_sync(self, provider: str, version: str) -> bool:
        return (
            self._live_sync_enabled()
            and provider == "youtube"
            and self._versions.get(provider) == version
        )

    def _live_sync_enabled(self) -> bool:
        return self._cookie_sync is not None and set(self._versions) == {"youtube"}

    def _validated_payload(self, provider: str, version: str) -> bytes:
        profile = _profile_for_key(provider)
        if ProviderAccessMode.OPERATOR_MANAGED not in profile.access_modes:
            raise RunnerFailure("provider_session_not_allowed", status=422)
        return validated_cookie_payload(
            self._source_root,
            provider,
            version,
            profile.cookie_domain_allowlist,
            now=self._clock(),
            max_age_seconds=self._settings.runner_provider_session_max_age_seconds,
        )


def _profile_for_key(key: str) -> ProviderProfile:
    from app.runner.provider_registry import default_provider_registry

    for profile in default_provider_registry().profiles:
        if profile.key == key:
            return profile
    raise RunnerFailure("provider_session_not_allowed", status=422)
