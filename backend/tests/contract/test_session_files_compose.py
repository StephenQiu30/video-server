"""Explicit file overrides must not retain browser transport or writable secrets."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_file_override_replaces_browser_transport_for_verified_providers() -> None:
    source = (ROOT / "docker-compose-session-files.yml").read_text()
    document = yaml.load(source, Loader=yaml.BaseLoader)
    baseline = yaml.safe_load((ROOT / "docker-compose-prod.yml").read_text())[
        "services"
    ]
    assert set(document) == {"services"}
    assert set(document["services"]) == {
        f"{provider}-operator-runner" for provider in ("youtube", "douyin", "reddit")
    }
    for name, service in document["services"].items():
        provider = name.removesuffix("-operator-runner")
        assert set(service) == {"environment", "volumes"}
        expected = dict(baseline[name]["environment"])
        expected.pop("RUNNER_PROVIDER_COOKIE_SYNC_ROOT", None)
        expected["RUNNER_PROVIDER_COOKIE_FILE"] = "/run/provider-source/cookies.txt"
        assert service["environment"] == expected
        assert "RUNNER_PROVIDER_COOKIE_SYNC_ROOT" not in service["environment"]
        assert service["volumes"] == [
            {
                "type": "bind",
                "source": "${PROVIDER_SESSION_DIR:-./.provider-sessions}/" + provider,
                "target": "/run/provider-source",
                "read_only": "true",
                "bind": {"create_host_path": "false"},
            }
        ]
    assert source.count("environment: !override") == 3
