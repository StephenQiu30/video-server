from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from app.workers.analysis.agent_cli import (
    ANALYSIS_STORAGE_PROBE,
    _record_agent_failure,
    _verify_storage,
)


def test_run_command_delegates_to_the_locked_worker_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.workers.analysis import agent_cli
    from app.workers.analysis import main as worker_main

    called: list[object] = []
    settings = object()
    monkeypatch.setattr(worker_main, "main", called.append)
    monkeypatch.setattr(agent_cli, "_env_file", lambda _: Path("/tmp/.env.prod"))
    monkeypatch.setattr(agent_cli, "_settings", lambda _: settings)
    monkeypatch.setattr(sys, "argv", ["agent_cli", "run", "--env-file", "../.env"])

    agent_cli.main()

    assert called == [settings]


def test_env_file_is_resolved_and_must_exist(tmp_path: Path) -> None:
    from app.workers.analysis.agent_cli import _env_file

    existing = tmp_path / ".env.prod"
    existing.write_text("APP_ENV=test\n")

    assert _env_file(existing) == existing.resolve()
    with pytest.raises(SystemExit, match="environment file is unavailable"):
        _env_file(tmp_path / "missing.env")


@dataclass(frozen=True, slots=True)
class _Stat:
    size_bytes: int


class _Storage:
    def __init__(self, *, missing: bool = False, fails: bool = False):
        self.result = None if missing else _Stat(1)
        self.fails = fails
        self.requested: str | None = None

    async def stat(self, object_key: str) -> _Stat | None:
        self.requested = object_key
        if self.fails:
            raise RuntimeError("access denied")
        return self.result


@pytest.mark.asyncio
async def test_storage_probe_is_readable() -> None:
    storage = _Storage()

    await _verify_storage(storage)

    assert storage.requested == ANALYSIS_STORAGE_PROBE


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [_Storage(missing=True), _Storage(fails=True)])
async def test_storage_probe_reports_unavailable_without_leaking_details(
    storage: _Storage,
) -> None:
    with pytest.raises(SystemExit, match="not ready: analysis MinIO") as error:
        await _verify_storage(storage)

    assert "access denied" not in str(error.value)


def test_agent_failure_log_records_stack_without_exception_message(tmp_path) -> None:
    target = tmp_path / "agent" / "analysis-agent.error.log"

    try:
        raise RuntimeError("provider-secret-must-not-be-logged")
    except RuntimeError as error:
        _record_agent_failure(error, target)

    recorded = target.read_text(encoding="utf-8")
    assert "RuntimeError" in recorded
    assert "test_agent_failure_log" in recorded
    assert "provider-secret-must-not-be-logged" not in recorded
