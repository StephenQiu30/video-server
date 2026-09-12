"""Deterministic provider routing for media inspection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from app.domain.provider_access import (
    ProviderAccessPolicy,
    default_access_policy,
    provider_access_policies,
)
from app.domain.providers import ProviderAccessMode
from app.runner.provider_registry import provider_profile, provider_profile_for_key
from app.services.downloads import MediaInspectionFailure, RunnerInspection
from app.services.downloads.errors import (
    MediaInspectionConfigurationMissing,
    MediaInspectionPolicyNotAllowed,
)


class MediaInspectionClient(Protocol):
    """A concrete inspection strategy, such as an isolated runner pool."""

    async def inspect(self, url: str) -> RunnerInspection: ...


class MediaInspectionPipeline:
    """Route each provider to exactly one access mode for the whole operation."""

    def __init__(
        self,
        anonymous: MediaInspectionClient,
        operators: Mapping[str, MediaInspectionClient] | None = None,
        *,
        default_policies: Mapping[str, ProviderAccessPolicy] | None = None,
    ) -> None:
        self._anonymous = anonymous
        self._operators = dict(operators or {})
        self._defaults = dict(default_policies or {})
        for key, policy in self._defaults.items():
            profile = provider_profile_for_key(key)
            if policy not in provider_access_policies(key, profile.access_modes):
                raise ValueError("default provider access policy is not admitted")

    def resolve_access_policy(
        self, url: str, requested: ProviderAccessPolicy | None = None
    ) -> ProviderAccessPolicy:
        profile = provider_profile(url)
        selected = (
            requested
            or self._defaults.get(profile.key)
            or default_access_policy(profile.key, profile.access_modes)
        )
        if selected not in provider_access_policies(profile.key, profile.access_modes):
            raise MediaInspectionPolicyNotAllowed
        if (
            selected.access_mode is ProviderAccessMode.OPERATOR_MANAGED
            and profile.key not in self._operators
        ):
            raise MediaInspectionConfigurationMissing
        return selected

    async def inspect(
        self, url: str, *, access_policy: ProviderAccessPolicy | None = None
    ) -> RunnerInspection:
        selected = self.resolve_access_policy(url, access_policy)
        profile = provider_profile(url)
        access_mode = selected.access_mode
        client = (
            self._anonymous
            if access_mode is ProviderAccessMode.ANONYMOUS
            else self._operators[profile.key]
        )
        try:
            result = await client.inspect(url)
            if (
                result.access_context.access_mode is not access_mode
                or result.access_context.provider_key != profile.key
            ):
                raise MediaInspectionFailure("runner policy context mismatch")
            return result
        except MediaInspectionFailure as error:
            error.attributed_to(access_mode)
            raise
