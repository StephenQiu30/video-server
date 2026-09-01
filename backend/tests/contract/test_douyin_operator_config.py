from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_douyin_operator_uses_provider_scoped_duration_tolerance() -> None:
    expected = "${DOUYIN_DURATION_TOLERANCE_SECONDS:-5}"

    for filename in ("docker-compose.yml", "docker-compose-prod.yml"):
        document = yaml.safe_load((ROOT / filename).read_text(encoding="utf-8"))
        environment = document["services"]["douyin-operator-runner"]["environment"]

        assert environment["RUNNER_DURATION_TOLERANCE_SECONDS"] == expected

    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "DOUYIN_DURATION_TOLERANCE_SECONDS=5" in env_example
