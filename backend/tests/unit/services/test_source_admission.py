from app.domain.downloads import AccessDecision
from app.services.downloads.source_admission import classify_restricted_source


def test_wechat_channels_public_share_continues_to_provider_runner() -> None:
    assert classify_restricted_source("https://weixin.qq.com/sph/AbCdEf12") is None


def test_qqvideo_single_video_reaches_runner_without_forcing_login() -> None:
    assert (
        classify_restricted_source(
            "https://v.qq.com/x/cover/example123/q326831cny0.html"
        )
        is None
    )


def test_known_platform_host_never_falls_back_to_generic() -> None:
    for url in (
        "https://v.qq.com/channel/cartoon",
        "https://weixin.qq.com/example",
        "https://mp.weixin.qq.com/profile",
    ):
        result = classify_restricted_source(url)
        assert result is not None
        assert result.access_decision is AccessDecision.UNSUPPORTED


def test_public_article_requires_discovery() -> None:
    result = classify_restricted_source("https://mp.weixin.qq.com/s/AbCdEf123")

    assert result is not None
    assert result.provider_key == "wechat_official_account_article"
    assert result.access_decision is AccessDecision.BLOCKED
    assert result.restriction_reason == "article_discovery_required"


def test_unrelated_source_continues_to_provider_runner() -> None:
    assert classify_restricted_source("https://media.example/video/1") is None


def test_configured_tencent_single_video_can_reach_operator_runner() -> None:
    assert (
        classify_restricted_source(
            "https://v.qq.com/x/cover/mzc00200fr1ry1o/m00441h6knj.html",
        )
        is None
    )


def test_operator_enablement_does_not_allow_playlists_or_arbitrary_ports() -> None:
    for url in (
        "https://v.qq.com/channel/cartoon",
        "https://v.qq.com/x/cover/example123.html",
        "https://v.qq.com:8443/x/page/q326831cny0.html",
    ):
        result = classify_restricted_source(url)
        assert result is not None
        assert result.access_decision is AccessDecision.UNSUPPORTED
