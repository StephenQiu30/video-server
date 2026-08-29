"""Operator-managed provider session isolation for the media runner."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import stat
import tempfile
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path

from app.domain.providers import ProviderAccessContextRef, ProviderAccessMode
from app.runner.errors import RunnerFailure
from app.runner.provider_registry import ProviderProfile, provider_profile
from app.runner.settings import RunnerSettings

_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_NETSCAPE_HEADERS = (
    b"# Netscape HTTP Cookie File",
    b"# HTTP Cookie File",
)


class ProviderSessionStore:
    """Validate immutable Cookie sources and issue per-operation writable jars."""

    def __init__(
        self,
        settings: RunnerSettings,
        *,
        clock: Callable[[], float] = time.time,
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
        if settings.runner_access_mode is ProviderAccessMode.OPERATOR_MANAGED:
            self._prepare_temp_root()

    def is_ready(self) -> bool:
        if self._settings.runner_access_mode is ProviderAccessMode.ANONYMOUS:
            return True
        try:
            for provider, version in self._versions.items():
                self._validated_source(provider, version)
        except RunnerFailure:
            return False
        return True

    def context_for(
        self, source: str | ProviderProfile
    ) -> ProviderAccessContextRef:
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
            source = self._validated_source(context.provider_key, version)
            operation_dir = Path(
                tempfile.mkdtemp(
                    prefix=f"{context.provider_key}-",
                    dir=self._temp_root,
                )
            )
            os.chmod(operation_dir, 0o700)
            jar = operation_dir / "cookies.txt"
            try:
                payload = _read_regular_file(source)
                descriptor = os.open(
                    jar,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | _no_follow(),
                    0o600,
                )
                with os.fdopen(descriptor, "wb", closefd=True) as output:
                    output.write(payload)
                    output.flush()
                    os.fsync(output.fileno())
                if os.name == "posix" and stat.S_IMODE(jar.stat().st_mode) != 0o600:
                    raise RunnerFailure("provider_session_unavailable", status=503)
                yield jar
            finally:
                shutil.rmtree(operation_dir, ignore_errors=True)

    def _validated_source(self, provider: str, version: str) -> Path:
        if _VERSION.fullmatch(version) is None:
            raise RunnerFailure("credential_rejected", status=422)
        profile = _profile_for_key(provider)
        if ProviderAccessMode.OPERATOR_MANAGED not in profile.access_modes:
            raise RunnerFailure("provider_session_not_allowed", status=422)
        candidate = self._source_root / provider / f"{version}.cookies.txt"
        if candidate.is_symlink():
            raise RunnerFailure("credential_rejected", status=422)
        source = candidate.resolve()
        if not source.is_relative_to(self._source_root):
            raise RunnerFailure("credential_rejected", status=422)
        self._validate_freshness(source)
        payload = _read_regular_file(source)
        _validate_netscape_cookie(payload, profile.cookie_domain_allowlist)
        return source

    def _validate_freshness(self, source: Path) -> None:
        max_age = self._settings.runner_provider_session_max_age_seconds
        if max_age <= 0:
            return
        try:
            age = self._clock() - source.stat().st_mtime
        except OSError as exc:
            raise RunnerFailure("credential_required", status=422) from exc
        if age < 0 or age > max_age:
            raise RunnerFailure("provider_session_unavailable", status=503)

    def _prepare_temp_root(self) -> None:
        self._temp_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self._temp_root.lstat()
        if not stat.S_ISDIR(info.st_mode) or self._temp_root.is_symlink():
            raise RunnerFailure("provider_session_unavailable", status=503)
        os.chmod(self._temp_root, 0o700)


def _profile_for_key(key: str) -> ProviderProfile:
    from app.runner.provider_registry import default_provider_registry

    for profile in default_provider_registry().profiles:
        if profile.key == key:
            return profile
    raise RunnerFailure("provider_session_not_allowed", status=422)


def _read_regular_file(path: Path) -> bytes:
    try:
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise RunnerFailure("credential_rejected", status=422)
        if info.st_size <= 0 or info.st_size > 1024**2:
            raise RunnerFailure("credential_rejected", status=422)
        descriptor = os.open(path, os.O_RDONLY | _no_follow())
        current = os.fstat(descriptor)
        if not stat.S_ISREG(current.st_mode) or current.st_ino != info.st_ino:
            os.close(descriptor)
            raise RunnerFailure("credential_rejected", status=422)
        with os.fdopen(descriptor, "rb", closefd=True) as source:
            payload = source.read(1024**2 + 1)
    except RunnerFailure:
        raise
    except OSError as exc:
        raise RunnerFailure("credential_required", status=422) from exc
    if len(payload) > 1024**2:
        raise RunnerFailure("credential_rejected", status=422)
    return payload


def _validate_netscape_cookie(payload: bytes, allowlist: frozenset[str]) -> None:
    lines = payload.splitlines()
    valid_header = lines and any(
        lines[0].startswith(header) for header in _NETSCAPE_HEADERS
    )
    if not valid_header:
        raise RunnerFailure("credential_rejected", status=422)
    found = False
    for line in lines[1:]:
        if not line or (line.startswith(b"#") and not line.startswith(b"#HttpOnly_")):
            continue
        fields = line.split(b"\t")
        if len(fields) != 7:
            raise RunnerFailure("credential_rejected", status=422)
        raw_domain = fields[0].removeprefix(b"#HttpOnly_")
        try:
            domain = raw_domain.decode("ascii").lstrip(".").casefold()
        except UnicodeDecodeError as exc:
            raise RunnerFailure("credential_rejected", status=422) from exc
        if not any(domain == item or domain.endswith(f".{item}") for item in allowlist):
            raise RunnerFailure("credential_rejected", status=422)
        found = True
    if not found:
        raise RunnerFailure("credential_rejected", status=422)


def _no_follow() -> int:
    return getattr(os, "O_NOFOLLOW", 0)
