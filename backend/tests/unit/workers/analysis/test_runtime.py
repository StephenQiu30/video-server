from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.workers.analysis.providers import (
    analysis_model_config,
    transcription_config,
)
from app.workers.analysis.sweeper import AnalysisRecoverySweeper
from pydantic import SecretStr


def test_worker_builds_ollama_or_deepseek_analysis_config() -> None:
    settings = Settings(app_env="test")
    ollama = analysis_model_config(settings)
    assert ollama.provider == "ollama"
    assert ollama.model == "qwen3:latest"

    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        analysis_model_config(Settings(app_env="test", analysis_provider="deepseek"))

    deepseek = analysis_model_config(
        Settings(
            app_env="test",
            analysis_provider="deepseek",
            deepseek_api_key=SecretStr("controlled-deepseek-key"),
        )
    )
    assert deepseek.provider == "deepseek"
    assert deepseek.model == "deepseek-v4-flash"
    assert "controlled-deepseek-key" not in repr(deepseek)


def test_transcription_config_requires_its_own_secret() -> None:
    settings = Settings(app_env="test")
    assert settings.openai_api_key is None
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        transcription_config(settings)

    provider = transcription_config(
        Settings(app_env="test", openai_api_key=SecretStr("controlled-key"))
    )
    assert provider.model == "gpt-4o-mini-transcribe"
    assert "controlled-key" not in repr(provider)


class FakeRecovery:
    def __init__(self) -> None:
        self.stale = (uuid4(),)
        self.ready = (uuid4(),)
        self.calls: list[tuple[str, int]] = []

    async def reclaim_stale(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[object, ...]:
        self.calls.append(("stale", limit))
        return self.stale

    async def release_ready_retries(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[object, ...]:
        self.calls.append(("ready", limit))
        return self.ready


@pytest.mark.asyncio
async def test_recovery_sweeper_reclaims_then_requeues_ready_jobs() -> None:
    repository = FakeRecovery()
    now = datetime(2026, 8, 6, tzinfo=UTC)
    sweeper = AnalysisRecoverySweeper(
        repository,  # type: ignore[arg-type]
        lambda: now,
    )

    assert await sweeper.tick() == (repository.stale, repository.ready)
    assert repository.calls == [("stale", 100), ("ready", 100)]
