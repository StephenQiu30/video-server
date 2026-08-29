"""Policy-driven strategy chain for media inspection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from app.application.downloads import MediaInspectionFailure, RunnerInspection
from app.application.downloads.errors import (
    MediaInspectionAuthRequired,
    MediaInspectionFormatUnavailable,
    MediaInspectionLinkUnavailable,
    MediaInspectionSessionExpired,
    MediaInspectionTemporarilyUnavailable,
    MediaInspectionVerificationFailed,
)
from app.domain.providers import ProviderAccessMode
from app.runner.provider_registry import provider_profile


class MediaInspectionClient(Protocol):
    """A concrete inspection strategy, such as an isolated runner pool."""

    async def inspect(self, url: str) -> RunnerInspection: ...


@dataclass(frozen=True, slots=True)
class InspectionAttempt:
    """One ordered responsibility in the inspection chain."""

    access_mode: ProviderAccessMode
    client: MediaInspectionClient


class InspectionFailurePolicy:
    """Decide when the chain may continue and which diagnosis is actionable."""

    _ANONYMOUS_FALLBACK_ERRORS = (
        MediaInspectionAuthRequired,
        MediaInspectionFormatUnavailable,
        MediaInspectionLinkUnavailable,
        MediaInspectionTemporarilyUnavailable,
        MediaInspectionVerificationFailed,
    )
    _AUTHORITATIVE_OPERATOR_ERRORS = (
        MediaInspectionLinkUnavailable,
        MediaInspectionSessionExpired,
    )

    def should_continue(
        self,
        attempt: InspectionAttempt,
        error: MediaInspectionFailure,
        *,
        has_next: bool,
    ) -> bool:
        return (
            has_next
            and attempt.access_mode is ProviderAccessMode.ANONYMOUS
            and isinstance(error, self._ANONYMOUS_FALLBACK_ERRORS)
        )

    def select_failure(
        self,
        failures: tuple[tuple[InspectionAttempt, MediaInspectionFailure], ...],
    ) -> MediaInspectionFailure:
        if not failures:
            raise ValueError("inspection failures cannot be empty")
        final_attempt, final_error = failures[-1]
        if (
            final_attempt.access_mode is ProviderAccessMode.OPERATOR_MANAGED
            and isinstance(final_error, self._AUTHORITATIVE_OPERATOR_ERRORS)
        ):
            # A provider-scoped session has enough context to make definitive
            # session and content-availability decisions.
            return final_error
        # Operator runners are optional. Preserve the first public-path
        # diagnosis when a fallback fails for any other infrastructure reason.
        return failures[0][1]


class MediaInspectionPipeline:
    """Compose runner strategies as a bounded chain of responsibility."""

    def __init__(
        self,
        anonymous: MediaInspectionClient,
        operators: Mapping[str, MediaInspectionClient] | None = None,
        *,
        failure_policy: InspectionFailurePolicy | None = None,
    ) -> None:
        self._anonymous = anonymous
        self._operators = dict(operators or {})
        self._failure_policy = failure_policy or InspectionFailurePolicy()

    async def inspect(self, url: str) -> RunnerInspection:
        attempts = self._attempts_for(url)
        if not attempts:
            raise MediaInspectionAuthRequired
        failures: list[tuple[InspectionAttempt, MediaInspectionFailure]] = []
        for index, attempt in enumerate(attempts):
            try:
                return await attempt.client.inspect(url)
            except MediaInspectionFailure as error:
                error.attributed_to(attempt.access_mode)
                failures.append((attempt, error))
                if self._failure_policy.should_continue(
                    attempt,
                    error,
                    has_next=index + 1 < len(attempts),
                ):
                    continue
                break

        selected = self._failure_policy.select_failure(tuple(failures))
        final_error = failures[-1][1]
        if selected is final_error:
            raise selected
        raise selected from final_error

    def _attempts_for(self, url: str) -> tuple[InspectionAttempt, ...]:
        profile = provider_profile(url)
        attempts: list[InspectionAttempt] = []
        if ProviderAccessMode.ANONYMOUS in profile.access_modes:
            attempts.append(
                InspectionAttempt(ProviderAccessMode.ANONYMOUS, self._anonymous)
            )
        operator = self._operators.get(profile.key)
        if (
            ProviderAccessMode.OPERATOR_MANAGED in profile.access_modes
            and operator is not None
        ):
            attempts.append(
                InspectionAttempt(ProviderAccessMode.OPERATOR_MANAGED, operator)
            )
        return tuple(attempts)
