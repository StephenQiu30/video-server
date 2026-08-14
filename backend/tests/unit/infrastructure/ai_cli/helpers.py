from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from app.application.analysis_execution import (
    ScreenplayAnalysisRequest,
    VideoAnalysisRequest,
)
from app.runner.process import ProcessResult
from tests.unit.workers.analysis.fixtures import (
    valid_mapping,
    valid_screenplay_mapping,
)


def request(tmp_path: Path) -> VideoAnalysisRequest:
    workspace = tmp_path / "job"
    artifact = workspace / "input" / "video.bin"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"controlled-video")
    return VideoAnalysisRequest(
        artifact=artifact,
        workspace=workspace,
        duration_ms=2_000,
        size_bytes=artifact.stat().st_size,
        container="mp4",
        output_language="zh-CN",
        skill_id="director-breakdown",
        skill_instructions="按 Cut 逐镜头完成导演拉片分析。",
    )


def screenplay_request(tmp_path: Path) -> ScreenplayAnalysisRequest:
    workspace = tmp_path / "screenplay-job"
    screenplay = workspace / "input" / "screenplay.md"
    screenplay.parent.mkdir(parents=True)
    text = "INT. EDITING ROOM - NIGHT\n\n林舟发现结局素材消失了。\n"
    screenplay.write_text(text, encoding="utf-8")
    return ScreenplayAnalysisRequest(
        screenplay=screenplay,
        workspace=workspace,
        screenplay_text=text,
        source_scene_ids=("scene-1",),
        source_language="mixed",
        output_language="zh-CN",
        skill_id="screenplay-analysis",
        skill_instructions="分析结构、人物、场景和对白，并引用原文场景。",
    )


class FakeSupervisor:
    def __init__(self, *, provider: str, payload: object | None = None) -> None:
        self.provider = provider
        self.payload = payload if payload is not None else valid_mapping()
        self.argv: tuple[str, ...] = ()
        self.environment: dict[str, str] = {}
        self.input_bytes: bytes | None = None

    async def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_bytes: bytes | None = None,
    ) -> ProcessResult:
        self.argv = tuple(argv)
        self.environment = dict(env or {})
        self.input_bytes = input_bytes
        if self.provider == "codex":
            target = Path(self.argv[self.argv.index("--output-last-message") + 1])
            target.write_text(json.dumps(self.payload), encoding="utf-8")
            stdout = b""
        else:
            stdout = json.dumps({"structured_output": self.payload}).encode()
        return ProcessResult(0, stdout, b"", False, False)


def screenplay_supervisor() -> FakeSupervisor:
    return FakeSupervisor(provider="claude", payload=valid_screenplay_mapping())
