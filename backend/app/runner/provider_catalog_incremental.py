"""Strict public profiles added after the original provider catalog."""

from __future__ import annotations

import re
from urllib.parse import SplitResult

from app.domain.providers import (
    ProviderCapability,
    ProviderSupportStatus,
)
from app.runner.errors import RunnerFailure
from app.runner.provider_registry import ProviderProfile

_RUTUBE_VIDEO = re.compile(r"/(?:video|(?:play/)?embed)/[0-9a-z]{32}/?")
_RUTUBE_NUMERIC_EMBED = re.compile(r"/(?:video|play)/embed/[0-9]+/?")
_VK_VIDEO = re.compile(r"/(?:video|clip)-?[0-9]+_[0-9]+/?")
_PEERTUBE_VIDEO = re.compile(
    r"/(?:videos/(?:watch|embed)|w)/(?:[A-Za-z0-9_-]{22}|"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-"
    r"[0-9a-f]{12})/?",
    re.IGNORECASE,
)


def _strict_public_url(
    url: str,
    parsed: SplitResult,
    patterns: tuple[re.Pattern[str], ...],
) -> str:
    if (
        parsed.query
        or parsed.fragment
        or not any(pattern.fullmatch(parsed.path) for pattern in patterns)
    ):
        raise RunnerFailure("provider_unsupported", status=422)
    return url


def _rutube_url(url: str, parsed: SplitResult) -> str:
    return _strict_public_url(
        url,
        parsed,
        (_RUTUBE_VIDEO, _RUTUBE_NUMERIC_EMBED),
    )


def _vk_url(url: str, parsed: SplitResult) -> str:
    return _strict_public_url(url, parsed, (_VK_VIDEO,))


def _peertube_url(url: str, parsed: SplitResult) -> str:
    return _strict_public_url(url, parsed, (_PEERTUBE_VIDEO,))


def peertube_profile(hosts: frozenset[str]) -> ProviderProfile:
    if not hosts:
        raise ValueError("PeerTube profile requires approved instances")
    return ProviderProfile(
        key="peertube",
        display_name="PeerTube",
        hosts=hosts,
        version="peertube-approved-instance-v1",
        capabilities=frozenset(
            {
                ProviderCapability.SINGLE_VIDEO,
                ProviderCapability.AUDIO_VIDEO_SPLIT,
            }
        ),
        support_status=ProviderSupportStatus.UNKNOWN,
        canary_suite="peertube-approved-instance-single-video",
        normalize_url=_peertube_url,
    )


INCREMENTAL_PUBLIC_PROFILES: tuple[ProviderProfile, ...] = (
    ProviderProfile(
        key="rutube",
        display_name="Rutube",
        hosts=frozenset({"rutube.ru", "www.rutube.ru"}),
        version="rutube-public-v1",
        capabilities=frozenset(
            {
                ProviderCapability.SINGLE_VIDEO,
                ProviderCapability.AUDIO_VIDEO_SPLIT,
            }
        ),
        support_status=ProviderSupportStatus.UNKNOWN,
        canary_suite="rutube-public-single-video",
        normalize_url=_rutube_url,
    ),
    ProviderProfile(
        key="vk",
        display_name="VK Clips",
        hosts=frozenset(
            {
                "vk.com",
                "m.vk.com",
                "new.vk.com",
                "vksport.vk.com",
                "vk.ru",
                "m.vk.ru",
                "new.vk.ru",
                "vksport.vk.ru",
                "vkvideo.ru",
                "m.vkvideo.ru",
                "new.vkvideo.ru",
                "vksport.vkvideo.ru",
            }
        ),
        version="vk-public-v1",
        capabilities=frozenset(
            {
                ProviderCapability.SINGLE_VIDEO,
                ProviderCapability.SHORT_VIDEO,
                ProviderCapability.AUDIO_VIDEO_SPLIT,
            }
        ),
        support_status=ProviderSupportStatus.UNKNOWN,
        canary_suite="vk-public-video-or-clip",
        normalize_url=_vk_url,
    ),
)
