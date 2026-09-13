"""The optional browser source changes only YouTube's credential transport."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_browser_override_is_scoped_to_one_existing_runner() -> None:
    source = (ROOT / "docker-compose-browser.yml").read_text()
    document = yaml.load(source, Loader=yaml.BaseLoader)
    assert set(document) == {"services"}
    assert set(document["services"]) == {"youtube-operator-runner"}
    service = document["services"]["youtube-operator-runner"]
    assert set(service) == {"environment", "volumes"}
    assert service["environment"] == {
        "RUNNER_PROVIDER_COOKIE_FILE": "null",
        "RUNNER_PROVIDER_COOKIE_SYNC_ROOT": "/run/provider-source",
    }
    assert service["volumes"] == [
        {
            "type": "bind",
            "source": "${PROVIDER_COOKIE_AGENT_RUNTIME_DIR:-${HOME}/Library/Caches/"
            "FrameFetch/provider-cookie-agent}/youtube",
            "target": "/run/provider-source",
            "read_only": "false",
            "bind": {"create_host_path": "false"},
        }
    ]
    # Remove the file source, including any same-named host environment value.
    assert "RUNNER_PROVIDER_COOKIE_FILE: !reset null" in source
