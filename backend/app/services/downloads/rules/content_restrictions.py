"""Stable reasons for recognized paid-content restrictions, not access grants."""

from enum import StrEnum


class ContentRestriction(StrEnum):
    PREVIEW_ONLY = "content_preview_only"
    SUPPORTER_ONLY = "content_supporter_only"
    PAID_ONLY = "content_paid_only"
    EXPORT_REQUIRED = "content_export_required"
    METADATA_INVALID = "content_access_metadata_invalid"
