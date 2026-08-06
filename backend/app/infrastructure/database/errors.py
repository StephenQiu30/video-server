"""Stable persistence errors translated by the application layer."""

from app.application.downloads.errors import (
    PersistenceConflict,
    PersistenceIdempotencyConflict,
    PersistenceNotFound,
)


class RepositoryError(RuntimeError):
    """Base class for persistence failures safe to classify upstream."""


class RepositoryNotFound(RepositoryError, PersistenceNotFound):
    """A requested aggregate does not exist."""


class IdempotencyConflict(RepositoryError, PersistenceIdempotencyConflict):
    """An idempotency key was reused for a different request."""


class LeaseConflict(RepositoryError, PersistenceConflict):
    """A stale or foreign worker attempted to mutate a leased job."""


class RepositoryConflict(RepositoryError, PersistenceConflict):
    """Stored deterministic data conflicts with the submitted data."""
