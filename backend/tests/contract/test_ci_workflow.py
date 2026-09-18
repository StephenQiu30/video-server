from pathlib import Path

import yaml

WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github/workflows/ci.yml"


def test_ci_is_limited_to_deterministic_system_tests() -> None:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]

    assert set(jobs) == {"backend-tests", "frontend-tests"}
    assert {job["name"] for job in jobs.values()} == {
        "Backend tests",
        "Frontend tests",
    }

    commands = "\n".join(
        step.get("run", "") for job in jobs.values() for step in job["steps"]
    )
    assert "pytest -q" in commands
    assert "pnpm test" in commands
    assert "pnpm build" in commands
    assert "docker compose" not in commands
    assert "npm audit" not in commands


def test_ci_actions_are_pinned_to_commits() -> None:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))

    for job in workflow["jobs"].values():
        for step in job["steps"]:
            reference = step.get("uses")
            if reference is None:
                continue
            _, revision = reference.rsplit("@", maxsplit=1)
            assert len(revision) == 40
            assert all(character in "0123456789abcdef" for character in revision)
