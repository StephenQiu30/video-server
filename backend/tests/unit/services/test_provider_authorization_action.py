from app.services.provider_types import (
    ProviderAccessMode,
    ProviderAuthorizationAction,
    ProviderKey,
    ProviderSupportStatus,
    provider_authorization_action,
)


def action(
    provider: ProviderKey,
    *,
    modes: tuple[ProviderAccessMode, ...] = (
        ProviderAccessMode.ANONYMOUS,
        ProviderAccessMode.OPERATOR_MANAGED,
    ),
    status: ProviderSupportStatus = ProviderSupportStatus.ACCESS_REQUIRED,
    last_check_succeeded: bool | None = False,
) -> ProviderAuthorizationAction:
    return provider_authorization_action(
        provider,
        access_modes=modes,
        status=status,
        last_check_succeeded=last_check_succeeded,
    )


def test_explicit_account_failure_exposes_deployment_managed_recovery() -> None:
    for provider in (ProviderKey.YOUTUBE, ProviderKey.DOUYIN, ProviderKey.REDDIT):
        assert action(provider) is ProviderAuthorizationAction.MANAGED_SESSION


def test_baseline_or_guest_state_never_requests_account_authorization() -> None:
    assert (
        action(ProviderKey.DOUYIN, last_check_succeeded=None)
        is ProviderAuthorizationAction.NONE
    )
    assert (
        action(
            ProviderKey.DOUYIN,
            modes=(ProviderAccessMode.ANONYMOUS, ProviderAccessMode.GUEST),
        )
        is ProviderAuthorizationAction.NONE
    )
    assert (
        action(ProviderKey.DOUYIN, status=ProviderSupportStatus.DEGRADED)
        is ProviderAuthorizationAction.NONE
    )


def test_public_providers_do_not_expose_local_browser_recovery() -> None:
    for provider in (
        ProviderKey.BILIBILI,
        ProviderKey.XIAOHONGSHU,
        ProviderKey.X,
        ProviderKey.INSTAGRAM,
        ProviderKey.FACEBOOK,
        ProviderKey.PINTEREST,
    ):
        assert action(provider) is ProviderAuthorizationAction.NONE
