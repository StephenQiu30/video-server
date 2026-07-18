"""Stable safe errors for the source-resolution persistence boundary."""

from __future__ import annotations

from video_server.errors import DomainError


class ResolutionCreatePersistenceError(DomainError):
    """A safe source-resolution create failure."""


def rejected_create(code: str) -> ResolutionCreatePersistenceError:
    errors = {
        "IDEMPOTENCY_KEY_INVALID": (
            "The idempotency key must contain 16 to 128 visible ASCII characters.",
            False,
            None,
            None,
        ),
        "IDEMPOTENCY_CONFLICT": (
            "The idempotency key was already used for a different request.",
            False,
            None,
            None,
        ),
        "RIGHTS_CONFIRMATION_REQUIRED": (
            "Rights confirmation is required before source resolution.",
            False,
            "/rights_confirmed",
            None,
        ),
        "RIGHTS_STATEMENT_STALE": (
            "The submitted rights statement is no longer current.",
            False,
            "/rights_statement_version",
            ("refresh_rights_statement",),
        ),
        "RIGHTS_STATEMENT_UNAVAILABLE": (
            "The current rights statement is unavailable.",
            True,
            None,
            None,
        ),
    }
    detail, retryable, field, actions = errors[code]
    return ResolutionCreatePersistenceError(
        code,
        detail,
        retryable=retryable,
        field=field,
        actions=actions,
    )


def internal_create_error() -> ResolutionCreatePersistenceError:
    return ResolutionCreatePersistenceError(
        "INTERNAL_ERROR",
        "The source resolution could not be created.",
    )
