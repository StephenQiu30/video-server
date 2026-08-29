from __future__ import annotations

import plistlib
from pathlib import Path

from app.workers.analysis.launchd import write_launch_agent


def test_launch_agent_supervises_host_analysis_worker(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "backend" / ".venv" / "bin").mkdir(parents=True)
    cli = tmp_path / "bin" / "codex"
    cli.parent.mkdir()
    cli.touch()
    output = tmp_path / "state" / "worker.plist"
    log = tmp_path / "worker.log"

    write_launch_agent(
        project=project,
        cli_binary=cli,
        output=output,
        log=log,
    )

    with output.open("rb") as stream:
        payload = plistlib.load(stream)
    assert payload["KeepAlive"] is True
    assert payload["RunAtLoad"] is True
    assert payload["Label"] == "com.stephenqiu.video.analysis-worker"
    assert payload["ProgramArguments"][-2:] == [
        "-m",
        "app.workers.analysis.main",
    ]
    assert str(cli.parent.resolve()) in payload["EnvironmentVariables"]["PATH"]
