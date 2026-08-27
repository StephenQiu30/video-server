"""Bounded, side-effect-free protection classification for media manifests."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.downloads.inspection import ProtectionState

_HLS_KEY = re.compile(r"^#EXT-X-(?:SESSION-)?KEY:(.*)$", re.MULTILINE)
_HLS_METHOD = re.compile(r"(?:^|,)METHOD=([^,]+)")
_DASH_PROTECTION = re.compile(
    rb"<(?:[A-Za-z_][\w.-]*:)?ContentProtection\b|"
    rb"<(?:[A-Za-z_][\w.-]*:)?pssh\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ProtectionClassification:
    state: ProtectionState
    reason: str | None = None


def classify_hls_manifest(
    payload: bytes,
    *,
    max_bytes: int = 1024 * 1024,
) -> ProtectionClassification:
    if not payload or len(payload) > max_bytes or b"\x00" in payload:
        return ProtectionClassification(ProtectionState.UNKNOWN, "manifest_invalid")
    try:
        document = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ProtectionClassification(ProtectionState.UNKNOWN, "manifest_invalid")
    if not document.lstrip().startswith("#EXTM3U"):
        return ProtectionClassification(ProtectionState.UNKNOWN, "manifest_invalid")
    for attributes in _HLS_KEY.findall(document):
        method = _HLS_METHOD.search(attributes)
        if method is None:
            return ProtectionClassification(
                ProtectionState.UNKNOWN, "hls_key_method_unknown"
            )
        normalized = method.group(1).strip().strip('"').upper()
        if normalized == "NONE":
            continue
        if normalized.startswith("SAMPLE-AES"):
            return ProtectionClassification(ProtectionState.DRM, "hls_drm")
        if normalized == "AES-128":
            return ProtectionClassification(ProtectionState.ENCRYPTED, "hls_encrypted")
        return ProtectionClassification(
            ProtectionState.UNKNOWN, "hls_key_method_unknown"
        )
    return ProtectionClassification(ProtectionState.CLEAR)


def classify_dash_manifest(
    payload: bytes,
    *,
    max_bytes: int = 1024 * 1024,
) -> ProtectionClassification:
    if (
        not payload
        or len(payload) > max_bytes
        or b"<!DOCTYPE" in payload.upper()
        or b"<MPD" not in payload.upper()
    ):
        return ProtectionClassification(ProtectionState.UNKNOWN, "manifest_invalid")
    if _DASH_PROTECTION.search(payload):
        return ProtectionClassification(ProtectionState.DRM, "dash_drm")
    return ProtectionClassification(
        ProtectionState.UNKNOWN, "dash_download_not_enabled"
    )
