from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from app.runner.commands import MediaCommands
from app.runner.errors import RunnerFailure
from app.runner.process import ProcessResult
from helpers import settings


class FailingSupervisor:
    def __init__(self, stderr: bytes) -> None:
        self.stderr = stderr

    async def run(
        self,
        _argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        del cwd, timeout_seconds, env
        return ProcessResult(1, b"", self.stderr, False, False)


class RecordingSupervisor:
    def __init__(self) -> None:
        self.argv: Sequence[str] = ()
        self.env: Mapping[str, str] = {}

    async def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        del cwd, timeout_seconds
        self.argv = argv
        self.env = env or {}
        return ProcessResult(0, b"{}", b"", False, False)


@pytest.mark.asyncio
async def test_inspection_classifies_douyin_fresh_cookie_requirement(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: Fresh cookies (not necessarily logged in) are needed"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://www.douyin.com/video/123", tmp_path)

    assert caught.value.code == "provider_access_required"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_inspection_classifies_youtube_bot_confirmation_requirement(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: Sign in to confirm you're not a bot. "
            b"Use --cookies for authentication"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://www.youtube.com/watch?v=owned", tmp_path)

    assert caught.value.code == "provider_access_required"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_inspection_classifies_vimeo_login_requirement(tmp_path: Path) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: The Vimeo extractor only works when logged-in. Use --cookies"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://vimeo.com/76979871", tmp_path)

    assert caught.value.code == "provider_access_required"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_youtube_uses_operator_managed_provider_egress(tmp_path: Path) -> None:
    supervisor = RecordingSupervisor()
    configured = settings(tmp_path).model_copy(
        update={
            "runner_provider_egress_proxies": {"youtube": "http://youtube-egress:3128"}
        }
    )
    commands = MediaCommands(configured, supervisor)

    await commands.inspect("https://www.youtube.com/watch?v=owned", tmp_path)

    assert supervisor.argv[supervisor.argv.index("--proxy") + 1] == (
        "http://youtube-egress:3128"
    )
    assert supervisor.env["HTTPS_PROXY"] == "http://youtube-egress:3128"
    assert "--cookies" not in supervisor.argv


@pytest.mark.asyncio
async def test_non_ytdlp_failures_keep_their_original_code(tmp_path: Path) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"Fresh cookies are needed"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.probe_remote("https://media.example/video", tmp_path)

    assert caught.value.code == "inspection_failed"
    assert caught.value.status == 502


@pytest.mark.asyncio
async def test_douyin_short_link_that_redirects_to_home_is_classified_as_unavailable(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: Unsupported URL: https://www.douyin.com/"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://v.douyin.com/KWku50HECg/", tmp_path)

    assert caught.value.code == "provider_link_unavailable"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_xhs_share_link_without_token_is_classified_as_unavailable(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: Unable to extract initial state"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://xhslink.com/m/expired", tmp_path)

    assert caught.value.code == "provider_link_unavailable"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_generic_unsupported_url_keeps_inspection_failure(tmp_path: Path) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: Unsupported URL: https://media.example/"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://media.example/video", tmp_path)

    assert caught.value.code == "inspection_failed"
    assert caught.value.status == 502


@pytest.mark.asyncio
async def test_wechat_channels_url_is_classified_as_unsupported(tmp_path: Path) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: Unsupported URL: https://channels.weixin.qq.com/finder-preview"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://weixin.qq.com/sph/AFWYoXF5Bw", tmp_path)

    assert caught.value.code == "provider_unsupported"
    assert caught.value.status == 422
