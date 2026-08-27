"""Fail-closed content entitlement checks before provider media access."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.providers import ProviderAccessMode
from app.runner.errors import RunnerFailure

_ALLOWED_YOUTUBE_AVAILABILITY = {"public", "unlisted"}
_RESTRICTED_AVAILABILITY = {
    "private": "content_private",
    "premium_only": "content_not_entitled",
    "subscriber_only": "content_not_entitled",
    "vip_only": "content_not_entitled",
    "paid": "content_not_entitled",
    "purchase_required": "content_not_entitled",
    "preview": "content_not_entitled",
    "needs_auth": "credential_required",
}
_OPERATOR_PROVIDER_POLICIES = frozenset(
    {
        "youtube",
        "tiktok",
        "douyin",
        "xiaohongshu",
        "reddit",
        "x",
        "instagram",
        "facebook",
    }
)


def enforce_media_rights(
    payload: Mapping[str, Any],
    *,
    provider_key: str,
    access_mode: ProviderAccessMode,
) -> None:
    if _has_drm(payload):
        raise RunnerFailure("drm_protected", status=422)
    availability = payload.get("availability")
    if isinstance(availability, str):
        normalized = availability.casefold()
        restricted = _RESTRICTED_AVAILABILITY.get(normalized)
        if restricted is not None:
            raise RunnerFailure(restricted, status=403)
        if (
            provider_key == "youtube"
            and normalized not in _ALLOWED_YOUTUBE_AVAILABILITY
        ):
            raise RunnerFailure("content_entitlement_unknown", status=422)
    if payload.get("is_private") is True:
        raise RunnerFailure("content_private", status=403)
    if any(
        payload.get(field) is True
        for field in (
            "is_premium",
            "is_member_only",
            "is_preview",
            "requires_purchase",
        )
    ):
        raise RunnerFailure("content_not_entitled", status=403)
    if access_mode is not ProviderAccessMode.OPERATOR_MANAGED:
        return
    if provider_key not in _OPERATOR_PROVIDER_POLICIES:
        raise RunnerFailure("provider_session_not_allowed", status=422)
    if provider_key == "youtube" and not isinstance(availability, str):
        raise RunnerFailure("content_entitlement_unknown", status=422)


def _has_drm(payload: Mapping[str, Any]) -> bool:
    if payload.get("has_drm") is True:
        return True
    formats = payload.get("formats")
    if not isinstance(formats, list) or not formats:
        return False
    playable = [item for item in formats if isinstance(item, dict)]
    return bool(playable) and all(item.get("has_drm") is True for item in playable)
