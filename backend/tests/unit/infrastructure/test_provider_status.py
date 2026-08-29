from app.domain.providers import ProviderAccessMode, ProviderSupportStatus
from app.infrastructure.provider_status import configured_provider_statuses


def test_statuses_expose_only_runtime_enabled_access_modes() -> None:
    statuses = {item.key: item for item in configured_provider_statuses()}

    assert statuses["youtube"].access_modes == (ProviderAccessMode.ANONYMOUS,)
    assert statuses["tiktok"].access_modes == (ProviderAccessMode.ANONYMOUS,)
    assert statuses["douyin"].status is ProviderSupportStatus.ACCESS_REQUIRED
    assert statuses["qqvideo"].access_modes == ()
    assert statuses["qqvideo"].status is ProviderSupportStatus.DISABLED
    assert statuses["qqvideo"].download_supported is False
    assert statuses["qqvideo"].user_action == (
        "支持识别腾讯视频单视频链接并引导官方播放；"
        "消费端私有接口、VIP、付费及 DRM 内容不提供下载。"
        "自有媒资请通过腾讯云 VOD 官方导出或上传明文文件。"
    )
    assert statuses["youku"].user_action == (
        "仅支持无需登录即可访问的公开、非 DRM 单视频；"
        "VIP、付费或试看内容请在优酷官方客户端播放。"
    )
    assert all(
        ProviderAccessMode.OPERATOR_MANAGED not in item.access_modes
        for item in statuses.values()
    )


def test_statuses_expose_only_the_configured_operator() -> None:
    statuses = {
        item.key: item for item in configured_provider_statuses(frozenset({"youtube"}))
    }

    assert statuses["youtube"].access_modes == (
        ProviderAccessMode.ANONYMOUS,
        ProviderAccessMode.OPERATOR_MANAGED,
    )
    assert statuses["douyin"].access_modes == (ProviderAccessMode.ANONYMOUS,)
