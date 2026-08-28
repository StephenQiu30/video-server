from __future__ import annotations

import plistlib
from pathlib import Path

from app.runner.provider_session_launchd import write_launch_agent


def test_launch_agent_supervises_provider_session_broker(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "backend" / ".venv" / "bin").mkdir(parents=True)
    output = tmp_path / "state" / "broker.plist"
    log = tmp_path / "broker.log"

    write_launch_agent(
        project=project,
        provider="wechat_channels",
        version="browser-live",
        interval_seconds=15,
        output=output,
        log=log,
    )

    with output.open("rb") as stream:
        payload = plistlib.load(stream)
    arguments = payload["ProgramArguments"]
    assert payload["KeepAlive"] is True
    assert payload["RunAtLoad"] is True
    assert payload["Label"].endswith("wechat_channels-session-broker")
    assert "app.runner.provider_session_broker" in arguments
    assert str(project / ".provider-secrets") in arguments
    assert (
        str(project / ".provider-sessions" / "wechat_channels" / "status.json")
        in arguments
    )
