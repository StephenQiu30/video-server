"""Installed extractor candidates; this contract makes no download claim."""

from typing import Literal

from pydantic import Field

from app.schemas.common import StrictModel


class EngineCandidateResponse(StrictModel):
    key: str = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1, max_length=256)
    upstream_working: bool


class EngineCatalogResponse(StrictModel):
    scope: Literal["anonymous_runner"] = "anonymous_runner"
    engine_version: str = Field(min_length=1, max_length=128)
    engine_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    expected_engine_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    pin_matches: bool
    bundled_plugins_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pot_provider_version: str | None = Field(default=None, max_length=128)
    manifest_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidates: tuple[EngineCandidateResponse, ...] = Field(
        min_length=1, max_length=10_000
    )
