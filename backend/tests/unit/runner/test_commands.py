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

    assert caught.value.code == "credential_required"
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

    assert caught.value.code == "egress_challenged"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_authenticated_youtube_bot_confirmation_is_expired_session(
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
        await commands.inspect(
            "https://www.youtube.com/watch?v=owned",
            tmp_path,
            cookie_jar=tmp_path / "cookies.txt",
        )

    assert caught.value.code == "credential_expired"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_wechat_missing_public_media_is_reported_as_restricted_content(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: WeChat Channels public media is not downloadable"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect(
            "https://weixin.qq.com/sph/AFWYoXF5Bw",
            tmp_path,
        )

    assert caught.value.code == "content_entitlement_unknown"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_inspection_classifies_unavailable_youtube_video(tmp_path: Path) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: [youtube] pqyXR30AoOs: Video unavailable"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://youtu.be/pqyXR30AoOs", tmp_path)

    assert caught.value.code == "provider_link_unavailable"
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

    assert caught.value.code == "credential_required"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_vimeo_inspection_checks_real_format_downloadability(
    tmp_path: Path,
) -> None:
    supervisor = RecordingSupervisor()
    commands = MediaCommands(settings(tmp_path), supervisor)

    await commands.inspect("https://vimeo.com/76979871", tmp_path)

    assert "--check-formats" in supervisor.argv
    assert supervisor.argv[-1] == "https://player.vimeo.com/video/76979871"


@pytest.mark.asyncio
async def test_download_classifies_selected_drm_format(tmp_path: Path) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: This format is DRM protected; Try selecting another format"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.download_stream(
            "https://vimeo.com/76979871",
            "hls-video",
            tmp_path / "video.input",
            tmp_path,
        )

    assert caught.value.code == "drm_protected"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_inspection_classifies_tiktok_webpage_challenge(tmp_path: Path) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: Unexpected response from webpage request"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect(
            "https://www.tiktok.com/@creator/video/123",
            tmp_path,
        )

    assert caught.value.code == "provider_temporarily_unavailable"
    assert caught.value.status == 503


@pytest.mark.asyncio
async def test_anonymous_youtube_media_403_is_an_egress_challenge(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: unable to download video data: HTTP Error 403: Forbidden"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.download_stream(
            "https://www.youtube.com/watch?v=owned",
            "401",
            tmp_path / "video.input",
            tmp_path,
        )

    assert caught.value.code == "egress_challenged"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_explicit_youtube_pot_rejection_keeps_specific_diagnosis(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: PO Token rejected: HTTP Error 403: Forbidden"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.download_stream(
            "https://www.youtube.com/watch?v=owned",
            "401",
            tmp_path / "video.input",
            tmp_path,
        )

    assert caught.value.code == "pot_rejected"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_inspection_classifies_tiktok_post_ip_restriction(tmp_path: Path) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: Your IP address is blocked from accessing this post"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect(
            "https://www.tiktok.com/@creator/video/123",
            tmp_path,
        )

    assert caught.value.code == "provider_geo_restricted"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_expired_tiktok_short_link_is_reported_as_unavailable(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: Unsupported URL: https://www.tiktok.com/?_r=1"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://www.tiktok.com/t/expired", tmp_path)

    assert caught.value.code == "provider_link_unavailable"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_dead_x_card_domain_is_reported_as_unavailable(tmp_path: Path) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: HTTP Error 500: Domain Not Found"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect(
            "https://twitter.com/example/status/123",
            tmp_path,
        )

    assert caught.value.code == "provider_link_unavailable"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_inspection_classifies_reddit_account_requirement(tmp_path: Path) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: Account authentication is required. Use --cookies"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect(
            "https://www.reddit.com/r/example/comments/123",
            tmp_path,
        )

    assert caught.value.code == "credential_required"
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
async def test_youtube_uses_service_managed_pot_without_cookies(tmp_path: Path) -> None:
    supervisor = RecordingSupervisor()
    configured = settings(tmp_path).model_copy(
        update={
            "runner_youtube_pot_base_url": "http://youtube-pot-provider:4416",
        }
    )
    commands = MediaCommands(configured, supervisor)

    await commands.inspect("https://www.youtube.com/watch?v=owned", tmp_path)

    assert "youtube:player_client=mweb,default" in supervisor.argv
    assert (
        "youtubepot-bgutilhttp:base_url=http://youtube-pot-provider:4416"
        in supervisor.argv
    )
    assert "--cookies" not in supervisor.argv


@pytest.mark.asyncio
async def test_tiktok_operator_command_uses_only_issued_cookie_jar(
    tmp_path: Path,
) -> None:
    supervisor = RecordingSupervisor()
    configured = settings(tmp_path).model_copy(
        update={"runner_tiktok_device_id": "7250000000000000001"}
    )
    commands = MediaCommands(configured, supervisor)
    cookie_jar = tmp_path / "operation.cookies.txt"

    await commands.inspect(
        "https://www.tiktok.com/@creator/video/123",
        tmp_path,
        cookie_jar=cookie_jar,
    )

    assert supervisor.argv[supervisor.argv.index("--cookies") + 1] == str(cookie_jar)
    assert "tiktok:device_id=7250000000000000001" in supervisor.argv


@pytest.mark.asyncio
async def test_non_allowlisted_provider_cannot_receive_cookie_jar(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(settings(tmp_path), RecordingSupervisor())

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect(
            "https://www.bilibili.com/video/BV1xx",
            tmp_path,
            cookie_jar=tmp_path / "operation.cookies.txt",
        )

    assert caught.value.code == "provider_session_not_allowed"


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
async def test_xhs_first_party_unavailable_note_is_not_an_extractor_regression(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: Xiaohongshu note unavailable"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect(
            "https://www.xiaohongshu.com/explore/6411f5d60000000013031939",
            tmp_path,
        )

    assert caught.value.code == "provider_link_unavailable"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_xhs_first_party_ip_risk_is_a_verification_failure(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: Xiaohongshu request verification required"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect(
            "https://www.xiaohongshu.com/explore/6411f5d60000000013031939",
            tmp_path,
        )

    assert caught.value.code == "egress_challenged"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_xhs_missing_video_formats_is_classified_as_extractor_regression(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: [xiaohongshu] 6411: No video formats found!"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect(
            "https://www.xiaohongshu.com/explore/6411f5d60000000013031939",
            tmp_path,
        )

    assert caught.value.code == "extractor_regression"
    assert caught.value.status == 502


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
async def test_wechat_channels_without_public_media_is_restricted(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: WeChat Channels public media is not downloadable"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://weixin.qq.com/sph/AFWYoXF5Bw", tmp_path)

    assert caught.value.code == "content_entitlement_unknown"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_kuaishou_expired_link_is_classified_as_unavailable(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: Kuaishou public link unavailable"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://v.kuaishou.com/expired", tmp_path)

    assert caught.value.code == "provider_link_unavailable"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_kuaishou_image_post_is_classified_as_unsupported(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: Kuaishou image posts are not supported by the video runner"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://v.kuaishou.com/image", tmp_path)

    assert caught.value.code == "provider_unsupported"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_facebook_image_post_is_classified_as_unsupported_media(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(
            b"ERROR: Facebook image and multi-asset posts are not supported "
            b"by the video runner"
        ),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://www.facebook.com/share/p/example/", tmp_path)

    assert caught.value.code == "provider_media_unsupported"
    assert caught.value.status == 422


@pytest.mark.asyncio
async def test_facebook_parse_failure_is_classified_as_extractor_regression(
    tmp_path: Path,
) -> None:
    commands = MediaCommands(
        settings(tmp_path),
        FailingSupervisor(b"ERROR: [facebook] 123: Cannot parse data"),
    )

    with pytest.raises(RunnerFailure) as caught:
        await commands.inspect("https://www.facebook.com/example/videos/123/", tmp_path)

    assert caught.value.code == "extractor_regression"
    assert caught.value.status == 502
