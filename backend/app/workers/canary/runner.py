"""Explicit access-route selection for Provider canaries."""

from __future__ import annotations

from collections.abc import Mapping

from app.application.downloads import (
    MediaInspectionAuthRequired,
    MediaInspectionFailure,
    RunnerInspection,
)
from app.domain.downloads import DownloadPlan
from app.domain.providers import ProviderAccessContextRef, ProviderAccessMode
from app.infrastructure.media_runner import MediaRunnerClient
from app.infrastructure.media_runner_models import (
    MediaRunnerClientError,
    RunnerArtifact,
)
from app.runner.provider_registry import provider_profile


class ProviderCanaryRunner:
    """Run exactly one declared route without business download fallback."""

    def __init__(
        self,
        anonymous: MediaRunnerClient,
        operators: Mapping[str, MediaRunnerClient] | None = None,
    ) -> None:
        self._anonymous = anonymous
        self._operators = dict(operators or {})

    async def inspect(
        self,
        url: str,
        *,
        access_mode: ProviderAccessMode,
    ) -> RunnerInspection:
        profile = provider_profile(url)
        if access_mode not in profile.access_modes:
            raise MediaInspectionAuthRequired(access_mode=access_mode)
        client = self._inspection_client(profile.key, access_mode)
        try:
            return await client.inspect(url)
        except MediaInspectionFailure as error:
            error.attributed_to(access_mode)
            raise

    async def download(
        self,
        task_id: str,
        url: str,
        plan: DownloadPlan,
        *,
        expected_provider_media_id: str,
        expected_extractor_key: str,
        access_context: ProviderAccessContextRef,
    ) -> RunnerArtifact:
        client = self._client_for_context(access_context)
        return await client.download(
            task_id,
            url,
            plan,
            expected_provider_media_id=expected_provider_media_id,
            expected_extractor_key=expected_extractor_key,
            access_context=access_context,
        )

    async def close(self) -> None:
        await self._anonymous.close()
        for operator in self._operators.values():
            await operator.close()

    def _inspection_client(
        self,
        provider_key: str,
        access_mode: ProviderAccessMode,
    ) -> MediaRunnerClient:
        if access_mode is ProviderAccessMode.ANONYMOUS:
            return self._anonymous
        operator = self._operators.get(provider_key)
        if operator is None:
            raise MediaInspectionAuthRequired(access_mode=access_mode)
        return operator

    def _client_for_context(
        self, context: ProviderAccessContextRef
    ) -> MediaRunnerClient:
        if context.access_mode is ProviderAccessMode.ANONYMOUS:
            return self._anonymous
        operator = self._operators.get(context.provider_key)
        if operator is None:
            raise MediaRunnerClientError("credential_required", 422)
        return operator
