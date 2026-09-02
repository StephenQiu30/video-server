"""Deterministic provider routing for media inspection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from app.application.downloads import MediaInspectionFailure, RunnerInspection
from app.application.downloads.errors import MediaInspectionAuthRequired
from app.domain.providers import ProviderAccessMode
from app.runner.provider_registry import provider_profile


class MediaInspectionClient(Protocol):
    """A concrete inspection strategy, such as an isolated runner pool."""

    async def inspect(self, url: str) -> RunnerInspection: ...


class MediaInspectionPipeline:
    """Route each provider to exactly one access mode for the whole operation."""

    def __init__(
        self,
        anonymous: MediaInspectionClient,
        operators: Mapping[str, MediaInspectionClient] | None = None,
    ) -> None:
        self._anonymous = anonymous
        self._operators = dict(operators or {})

    async def inspect(self, url: str) -> RunnerInspection:
        profile = provider_profile(url)
        operator = self._operators.get(profile.key)
        if (
            ProviderAccessMode.OPERATOR_MANAGED in profile.access_modes
            and operator is not None
        ):
            client = operator
            access_mode = ProviderAccessMode.OPERATOR_MANAGED
        elif ProviderAccessMode.ANONYMOUS in profile.access_modes:
            client = self._anonymous
            access_mode = ProviderAccessMode.ANONYMOUS
        else:
            raise MediaInspectionAuthRequired
        try:
            return await client.inspect(url)
        except MediaInspectionFailure as error:
            error.attributed_to(access_mode)
            raise
