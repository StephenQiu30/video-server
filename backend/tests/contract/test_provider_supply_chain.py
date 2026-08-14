from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUPPLY_CHAIN = ROOT / "supply-chain"


def test_provider_sbom_pins_runtime_components_and_licenses() -> None:
    document = json.loads((SUPPLY_CHAIN / "provider-sbom.json").read_text())
    components = {item["name"]: item for item in document["components"]}

    assert document["bomFormat"] == "CycloneDX"
    assert components["yt-dlp"]["version"] == "2026.7.4"
    assert "5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc" in components["yt-dlp"]["purl"]
    assert components["yt-dlp-ejs"]["version"] == "0.8.0"
    assert components["curl-cffi"]["version"] == "0.15.0"
    assert components["bgutil-ytdlp-pot-provider"]["version"] == "1.3.1"
    assert components["brainicism/bgutil-ytdlp-pot-provider"]["purl"].endswith(
        "sha256:1aaa43a0ca72dfca6a6d2129a0fb4a23465c25adb1b043f8aff829a20825646b"
    )
    assert all(component.get("licenses") for component in components.values())


def test_pyproject_and_compose_match_provider_sbom() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()
    compose = (ROOT.parent / "docker-compose.yml").read_text()
    dockerfile = (ROOT.parent / "Dockerfile").read_text()
    notices = (SUPPLY_CHAIN / "PROVIDER-NOTICES.md").read_text()

    assert '"bgutil-ytdlp-pot-provider==1.3.1"' in pyproject
    assert "bgutil-ytdlp-pot-provider:1.3.1@sha256:1aaa43a0" in compose
    assert "backend/supply-chain/" in dockerfile
    assert "GPL-3.0-only" in notices
    assert "MeTube, cobalt and gallery-dl are research references only" in notices
