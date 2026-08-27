from __future__ import annotations

import pytest
from app.domain.providers import ProviderAccessMode
from app.runner.entitlements import enforce_media_rights
from app.runner.errors import RunnerFailure


@pytest.mark.parametrize(
    "provider",
    (
        "tiktok",
        "douyin",
        "xiaohongshu",
        "reddit",
        "x",
        "instagram",
        "facebook",
    ),
)
def test_operator_allows_unrestricted_public_web_metadata(provider: str) -> None:
    enforce_media_rights(
        {"id": "123", "formats": [{"has_drm": None}]},
        provider_key=provider,
        access_mode=ProviderAccessMode.OPERATOR_MANAGED,
    )


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"is_private": True}, "content_private"),
        ({"availability": "needs_auth"}, "credential_required"),
        ({"is_member_only": True}, "content_not_entitled"),
    ],
)
def test_tiktok_operator_rejects_restricted_metadata(
    payload: dict[str, object],
    code: str,
) -> None:
    with pytest.raises(RunnerFailure) as caught:
        enforce_media_rights(
            payload,
            provider_key="tiktok",
            access_mode=ProviderAccessMode.OPERATOR_MANAGED,
        )

    assert caught.value.code == code


def test_unapproved_operator_provider_remains_blocked() -> None:
    with pytest.raises(RunnerFailure) as caught:
        enforce_media_rights(
            {},
            provider_key="generic",
            access_mode=ProviderAccessMode.OPERATOR_MANAGED,
        )

    assert caught.value.code == "provider_session_not_allowed"


@pytest.mark.parametrize(
    "payload",
    (
        {"is_private": True},
        {"is_premium": True},
        {"is_member_only": True},
        {"is_preview": True},
        {"requires_purchase": True},
        {"availability": "vip_only"},
        {"availability": "purchase_required"},
    ),
)
def test_anonymous_access_rejects_restricted_metadata(
    payload: dict[str, object],
) -> None:
    with pytest.raises(RunnerFailure) as caught:
        enforce_media_rights(
            payload,
            provider_key="qqvideo",
            access_mode=ProviderAccessMode.ANONYMOUS,
        )

    assert caught.value.code in {"content_private", "content_not_entitled"}
