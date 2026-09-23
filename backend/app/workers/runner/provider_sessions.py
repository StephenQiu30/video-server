"""Operator-managed provider session isolation for the media runner."""

from __future__ import annotations

import asyncio
import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from app.services.provider_guest import GuestScope
from app.services.provider_types import (
    ProviderAccessContextRef,
    ProviderAccessMode,
    ProviderKey,
    ProviderSessionVersion,
)
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.guest_material import read_guest_lease
from app.workers.runner.provider_cookie_file import ProviderCookieFile
from app.workers.runner.provider_cookie_sync import (
    ProviderCookieSync,
    ProviderCookieSyncClient,
)
from app.workers.runner.provider_credential_lease import (
    ProviderCredentialLeaseCoordinator,
)
from app.workers.runner.provider_registry import ProviderProfile, provider_profile
from app.workers.runner.provider_session_files import (
    operation_cookie,
    prepare_private_root,
    require_memory_backed_root,
    validated_cookie_payload,
)
from app.workers.runner.settings import RunnerSettings


def credential_revision(payload: bytes, secret: bytes) -> str:
    """Return the stable, keyed identity used for file-backed credentials."""
    return "file-" + hmac.digest(secret, payload, "sha256").hex()[:32]


class ProviderSessionStore:
    """Validate one-operation Cookie leases and issue tmpfs-backed jars."""

    def __init__(
        self,
        settings: RunnerSettings,
        *,
        cookie_sync: ProviderCookieSync | None = None,
        credential_lease: ProviderCredentialLeaseCoordinator | None = None,
        enforce_memory_backing: bool = True,
    ) -> None:
        self._settings = settings
        self._temp_root = settings.runner_provider_session_temp_root
        self._versions = dict(settings.runner_operator_session_versions)
        self._disabled_credentials: set[tuple[str, str]] = set()
        self._gate = asyncio.Semaphore(1)
        self._credential_lease = credential_lease
        if (
            self._credential_lease is None
            and settings.runner_credential_lease_redis_url
        ):
            self._credential_lease = ProviderCredentialLeaseCoordinator(
                settings.runner_credential_lease_redis_url,
                ttl_seconds=settings.runner_credential_lease_ttl_seconds,
                heartbeat_seconds=settings.runner_credential_lease_heartbeat_seconds,
            )
        sync_root = settings.runner_provider_cookie_sync_root
        self._cookie_file = (
            ProviderCookieFile(
                settings.runner_provider_cookie_file,
                require_lease=settings.runner_provider_source_require_lease,
            )
            if settings.runner_provider_cookie_file is not None
            else None
        )
        self._cookie_sync: ProviderCookieSync | None
        if cookie_sync is not None:
            self._cookie_sync = cookie_sync
        elif self._cookie_file is not None:
            self._cookie_sync = self._cookie_file
        elif sync_root is not None:
            self._cookie_sync = ProviderCookieSyncClient(sync_root)
        else:
            self._cookie_sync = None
        if settings.runner_access_mode in {
            ProviderAccessMode.OPERATOR_MANAGED,
            ProviderAccessMode.GUEST,
        }:
            prepare_private_root(self._temp_root)
            if enforce_memory_backing:
                require_memory_backed_root(self._temp_root)

    async def is_ready(self) -> bool:
        if self._settings.runner_access_mode is ProviderAccessMode.ANONYMOUS:
            return True
        if self._settings.runner_access_mode is ProviderAccessMode.GUEST:
            try:
                provider = self._settings.runner_guest_provider
                assert provider is not None
                self.context_for(_profile_for_key(provider))
                assert self._credential_lease is not None
                await self._credential_lease.ping()
                return True
            except RunnerFailure:
                return False
        cookie_sync = self._cookie_sync
        if cookie_sync is None or not self._versions:
            return False
        if self._credential_lease is not None:
            try:
                await self._credential_lease.ping()
            except RunnerFailure:
                return False
        for provider, version in self._versions.items():
            if (provider.value, version.value) in self._disabled_credentials:
                return False
            if not await cookie_sync.is_ready(provider, version):
                return False
        return True

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
        credential_version = None if version is None else version.value
        if mode is ProviderAccessMode.GUEST:
            if profile.key != self._settings.runner_guest_provider:
                raise RunnerFailure("provider_session_not_allowed", status=422)
            path = self._settings.runner_guest_cookie_file
            assert path is not None
            credential_version = read_guest_lease(
                path, self._guest_scope(profile), now=datetime.now(UTC)
            ).version
        if self._cookie_file is not None and version is not None:
            credential_version = self._file_revision(
                self._cookie_file.read(ProviderKey(profile.key), version)
            )
        self._require_credential_enabled(profile.key, credential_version)
        return ProviderAccessContextRef(
            provider_key=profile.key,
            profile_version=profile.version,
            access_mode=mode,
            credential_version_id=credential_version,
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
        *,
        allow_guest_refresh: bool = False,
    ) -> ProviderAccessContextRef:
        current = self.context_for(source)
        if current.runtime_revision == "legacy":
            expected = replace(expected, runtime_revision="legacy")
        if current.access_mode is ProviderAccessMode.ANONYMOUS:
            if current != expected:
                raise RunnerFailure("client_context_mismatch", status=409)
            return current
        if expected != current:
            if (
                allow_guest_refresh
                and current.access_mode is ProviderAccessMode.GUEST
                and expected.access_mode is ProviderAccessMode.GUEST
                and replace(
                    expected, credential_version_id=current.credential_version_id
                )
                == current
            ):
                # Only visitor material may rotate. Provider, engine, profile,
                # client and egress remain frozen; download re-inspects identity.
                return current
            if current.access_mode is ProviderAccessMode.GUEST:
                raise RunnerFailure("guest_context_required", status=503)
            raise RunnerFailure("credential_revoked", status=422)
        return current

    def disable_credential_version(self, context: ProviderAccessContextRef) -> None:
        """Quarantine one credential revision after an entitlement drift."""
        if context.access_mode is not ProviderAccessMode.OPERATOR_MANAGED:
            return
        credential_version = context.credential_version_id
        if credential_version is not None:
            self._disabled_credentials.add((context.provider_key, credential_version))

    @asynccontextmanager
    async def operation(
        self, context: ProviderAccessContextRef
    ) -> AsyncIterator[Path | None]:
        if context.access_mode is ProviderAccessMode.ANONYMOUS:
            yield None
            return
        if context.access_mode is ProviderAccessMode.GUEST:
            profile = _profile_for_key(context.provider_key)
            path = self._settings.runner_guest_cookie_file
            if (
                path is None
                or context.provider_key != self._settings.runner_guest_provider
            ):
                raise RunnerFailure("provider_session_not_allowed", status=422)
            self.validate_context(profile, context)
            assert self._credential_lease is not None
            async with (
                self._gate,
                self._credential_lease.hold(context.provider_key, "public-guest"),
            ):
                lease = read_guest_lease(
                    path, self._guest_scope(profile), now=datetime.now(UTC)
                )
                if lease.version != context.credential_version_id:
                    raise RunnerFailure("guest_context_required", status=503)
                with operation_cookie(
                    lease.payload, self._temp_root, context.provider_key
                ) as jar:
                    yield jar
            return
        raw_version = context.credential_version_id
        if raw_version is None:
            raise RunnerFailure("credential_required", status=422)
        self._require_credential_enabled(context.provider_key, raw_version)
        try:
            provider = ProviderKey(context.provider_key)
            version = (
                self._versions[provider]
                if self._cookie_file is not None
                else ProviderSessionVersion(raw_version)
            )
        except (ValueError, KeyError) as exc:
            raise RunnerFailure("credential_revoked", status=422) from exc
        async with self._gate:
            cookie_sync = self._cookie_sync
            if cookie_sync is None:
                raise RunnerFailure("credential_required", status=422)
            if self._credential_lease is None:
                async with (
                    _noop_lease(),
                    self._operation_cookie(
                        cookie_sync, provider, version, raw_version, context
                    ) as jar,
                ):
                    yield jar
            else:
                async with (
                    self._credential_lease.hold(context.provider_key, raw_version),
                    self._operation_cookie(
                        cookie_sync, provider, version, raw_version, context
                    ) as jar,
                ):
                    yield jar

    @asynccontextmanager
    async def _operation_cookie(
        self,
        cookie_sync: ProviderCookieSync,
        provider: ProviderKey,
        version: ProviderSessionVersion,
        raw_version: str,
        context: ProviderAccessContextRef,
    ) -> AsyncIterator[Path | None]:
        exported = await cookie_sync.sync(provider, version)
        if self._cookie_file is not None and not hmac.compare_digest(
            self._file_revision(exported), raw_version
        ):
            raise RunnerFailure("credential_revoked", status=422)
        payload = self._validated_payload(provider, exported)
        with operation_cookie(payload, self._temp_root, context.provider_key) as jar:
            yield jar

    def _file_revision(self, payload: bytes) -> str:
        # A keyed revision prevents identity changes between inspect and download
        # without exposing Cookie contents or an unkeyed credential hash.
        return credential_revision(payload, self._settings.hmac_secret_bytes)

    def _guest_scope(self, profile: ProviderProfile) -> GuestScope:
        return GuestScope(
            ProviderKey(profile.key),
            profile.version,
            profile.client_profile_id,
            self._settings.egress_affinity_for(profile.key),
        )

    def _require_credential_enabled(
        self, provider: str, credential_version: str | None
    ) -> None:
        if (
            credential_version is not None
            and (
                provider,
                credential_version,
            )
            in self._disabled_credentials
        ):
            raise RunnerFailure("credential_revoked", status=422)

    def _validated_payload(self, provider: ProviderKey, payload: bytes) -> bytes:
        profile = _profile_for_key(provider)
        if ProviderAccessMode.OPERATOR_MANAGED not in profile.access_modes:
            raise RunnerFailure("provider_session_not_allowed", status=422)
        return validated_cookie_payload(
            payload,
            profile.cookie_domain_allowlist,
        )

    async def close(self) -> None:
        if self._credential_lease is not None:
            await self._credential_lease.close()


@asynccontextmanager
async def _noop_lease() -> AsyncIterator[None]:
    yield


def _profile_for_key(key: str | ProviderKey) -> ProviderProfile:
    from app.workers.runner.provider_registry import default_provider_registry

    for profile in default_provider_registry().profiles:
        if profile.key == key:
            return profile
    raise RunnerFailure("provider_session_not_allowed", status=422)
