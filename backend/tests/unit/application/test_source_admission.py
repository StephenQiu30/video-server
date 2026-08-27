from app.application.downloads.source_admission import classify_restricted_source
from app.domain.downloads import AccessDecision, IdentityState


def test_wechat_channels_requires_user_export() -> None:
    result = classify_restricted_source("https://weixin.qq.com/sph/AbCdEf12")

    assert result is not None
    assert result.provider_key == "wechat_channels"
    assert result.access_decision is AccessDecision.EXPORT_REQUIRED
    assert result.identity_state is IdentityState.VERIFIED


def test_qqvideo_single_video_is_playback_only() -> None:
    result = classify_restricted_source(
        "https://v.qq.com/x/cover/example123/q326831cny0.html"
    )

    assert result is not None
    assert result.provider_media_id == "q326831cny0"
    assert result.access_decision is AccessDecision.PLAYBACK_ONLY
    assert result.restriction_reason == "tencent_consumer_download_disabled"


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

