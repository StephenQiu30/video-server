from __future__ import annotations

import json
from urllib.parse import urlsplit

from app.domain.providers import ProviderCanaryStage
from app.runner.errors import RunnerFailure
from app.runner.provider_registry import provider_profile
from app.runner.provider_urls import provider_request_url
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError


class ProviderCanaryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    provider_key: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    stage: ProviderCanaryStage
    url: SecretStr

    def safe_url(self) -> str:
        return self.url.get_secret_value()


def parse_canary_targets(value: SecretStr) -> tuple[ProviderCanaryTarget, ...]:
    try:
        document = json.loads(value.get_secret_value())
        if not isinstance(document, list):
            raise ValueError
        targets = tuple(ProviderCanaryTarget.model_validate(item) for item in document)
        _validate_targets(targets)
    except (
        TypeError,
        ValueError,
        ValidationError,
        json.JSONDecodeError,
        RunnerFailure,
    ):
        raise ValueError("provider canary targets are invalid") from None
    return targets


def _validate_targets(targets: tuple[ProviderCanaryTarget, ...]) -> None:
    identities: set[tuple[str, ProviderCanaryStage]] = set()
    for target in targets:
        identity = (target.target_id, target.stage)
        if identity in identities:
            raise ValueError
        identities.add(identity)
        url = target.safe_url()
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or provider_profile(url).key != target.provider_key
        ):
            raise ValueError
        provider_request_url(url)
