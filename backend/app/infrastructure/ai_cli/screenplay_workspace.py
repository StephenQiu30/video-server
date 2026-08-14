from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.application.analysis_execution import ScreenplayAnalysisRequest

from .errors import AnalysisCliError
from .workspace import JobFiles


def prepare_screenplay_job_files(
    request: ScreenplayAnalysisRequest,
    schema: dict[str, Any],
    prompt: str,
) -> JobFiles:
    try:
        root = request.workspace.resolve(strict=True)
        screenplay = request.screenplay.resolve(strict=True)
        if screenplay != root / "input" / "screenplay.md":
            raise OSError
    except OSError as exc:
        raise AnalysisCliError("artifact_integrity_failed") from exc
    try:
        for relative in (
            "policy",
            "work/chunks",
            "work/outputs",
            "output",
            "tmp",
        ):
            directory = root / relative
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
        _write_json(
            root / "input" / "manifest.json",
            {
                "input": "input/screenplay.md",
                "source_language": request.source_language,
                "source_scene_ids": list(request.source_scene_ids),
            },
        )
        schema_path = root / "policy" / "output-schema.json"
        _write_json(schema_path, schema)
        _write_text(root / "policy" / "prompt.txt", prompt)
        settings = root / "policy" / "claude-settings.json"
        _write_json(settings, _claude_policy(root))
        return JobFiles(root, schema_path, root / "output" / "result.json", settings)
    except OSError as exc:
        raise AnalysisCliError("invalid_analysis_workspace") from exc


def _write_json(path: Path, value: object) -> None:
    _write_text(path, json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)


def _claude_policy(root: Path) -> dict[str, Any]:
    return {
        "sandbox": {
            "enabled": True,
            "failIfUnavailable": True,
            "autoAllowBashIfSandboxed": False,
            "allowUnsandboxedCommands": False,
            "filesystem": {
                "denyRead": ["~/"],
                "allowRead": [str(root / "input")],
            },
            "network": {"strictAllowlist": True, "allowedDomains": []},
        },
        "permissions": {
            "deny": [
                "Bash",
                "Read",
                "Write",
                "Edit",
                "WebFetch",
                "WebSearch",
                "Agent",
            ]
        },
    }
