"""Browser transport remains explicitly scoped to approved existing runners."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("provider", ["youtube", "douyin", "reddit"])
def test_browser_override_is_scoped_to_existing_runners(provider: str) -> None:
    source = (ROOT / "docker-compose-browser.yml").read_text()
    document = yaml.load(source, Loader=yaml.BaseLoader)
    assert set(document) == {"services"}
    assert set(document["services"]) == {
        f"{key}-operator-runner" for key in ("youtube", "douyin", "reddit")
    }
    service = document["services"][f"{provider}-operator-runner"]
    assert set(service) == {"environment", "volumes"}
    assert service["environment"] == {
        "RUNNER_PROVIDER_COOKIE_FILE": "null",
        "RUNNER_PROVIDER_COOKIE_SYNC_ROOT": "/run/provider-source",
    }
    assert service["volumes"] == [
        {
            "type": "bind",
            "source": "${PROVIDER_COOKIE_AGENT_RUNTIME_DIR:-${HOME}/Library/Caches/"
            f"FrameFetch/provider-cookie-agent}}/{provider}",
            "target": "/run/provider-source",
            "read_only": "false",
            "bind": {"create_host_path": "false"},
        }
    ]
    # Remove the file source, including any same-named host environment value.
    assert "RUNNER_PROVIDER_COOKIE_FILE: !reset null" in source
