from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest
from app.workers.analysis import agent_lock
from app.workers.analysis import main as worker_main
from app.workers.analysis.agent_platforms import AgentPaths


def test_process_lock_rejects_second_agent_and_releases(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = AgentPaths(
        tmp_path / "definition",
        tmp_path / "state" / "agent.log",
        tmp_path / "state" / "agent.error.log",
    )
    monkeypatch.setattr(agent_lock, "agent_paths", lambda: paths)

    with agent_lock.analysis_agent_process_lock():
        with pytest.raises(agent_lock.AnalysisAgentAlreadyRunning):
            with agent_lock.analysis_agent_process_lock():
                pass

    with agent_lock.analysis_agent_process_lock():
        pass


def test_direct_worker_main_uses_the_process_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    @contextmanager
    def locked():
        events.append("locked")
        yield
        events.append("released")

    async def run(settings: object | None = None) -> None:
        assert settings is None
        events.append("run")

    monkeypatch.setattr(worker_main, "analysis_agent_process_lock", locked)
    monkeypatch.setattr(worker_main, "run", run)

    worker_main.main()

    assert events == ["locked", "run", "released"]
