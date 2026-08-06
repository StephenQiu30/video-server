from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.workers.analysis.main import _provider_config
from app.workers.analysis.sweeper import AnalysisRecoverySweeper
from pydantic import SecretStr


def test_provider_config_requires_secret_only_when_worker_is_built() -> None:
    settings = Settings(app_env="test")
    assert settings.openai_api_key is None
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        _provider_config(settings)

    provider = _provider_config(
        Settings(app_env="test", openai_api_key=SecretStr("controlled-key"))
    )
    assert provider.analysis_model == "gpt-5.6-luna"
    assert provider.transcription_model == "gpt-4o-mini-transcribe"
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
