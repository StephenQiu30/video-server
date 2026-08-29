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
    assert statuses["qqvideo"].user_action == "当前未开放此平台下载。"
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
