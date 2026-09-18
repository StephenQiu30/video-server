from app.domain.providers import ProviderAccessMode, ProviderSupportStatus
from app.integrations.provider_status import configured_provider_statuses


def test_statuses_expose_only_runtime_enabled_access_modes() -> None:
    statuses = {item.key: item for item in configured_provider_statuses()}

    assert statuses["youtube"].access_modes == (ProviderAccessMode.ANONYMOUS,)
    assert statuses["tiktok"].access_modes == (ProviderAccessMode.ANONYMOUS,)
    assert statuses["douyin"].status is ProviderSupportStatus.ACCESS_REQUIRED
    assert statuses["qqvideo"].access_modes == (ProviderAccessMode.ANONYMOUS,)
    assert statuses["qqvideo"].status is ProviderSupportStatus.UNKNOWN
    assert statuses["qqvideo"].download_supported is True
    assert "持久会话" in statuses["qqvideo"].user_action
    assert "待样本验证" in statuses["youku"].user_action
    assert statuses["qqvideo"].download_available is False
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


def test_personal_video_routes_do_not_claim_download_verification() -> None:
    statuses = {
        item.key: item
        for item in configured_provider_statuses(frozenset({"qqvideo", "youku"}))
    }
    for key in ("qqvideo", "youku"):
        assert ProviderAccessMode.OPERATOR_MANAGED in statuses[key].access_modes
        assert statuses[key].status is ProviderSupportStatus.UNKNOWN
        assert statuses[key].download_available is False
