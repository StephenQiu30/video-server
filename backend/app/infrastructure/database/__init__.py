"""PostgreSQL persistence adapter for inspections, jobs and the outbox."""

from .base import Base
from .completion_repository import build_artifact_object_key
from .contracts import (
    ArtifactCreate,
    ArtifactSnapshot,
    DownloadCreate,
    FormatCreate,
    FormatSnapshot,
    InspectionCreate,
    InspectionCreateResult,
    InspectionSnapshot,
    JobCreateResult,
    JobSnapshot,
    JobSourceSnapshot,
    OutboxSnapshot,
)
from .errors import (
    IdempotencyConflict,
    LeaseConflict,
    RepositoryConflict,
    RepositoryError,
    RepositoryNotFound,
)
from .models import (
    AnalysisArtifactLockRow,
    AnalysisJobRow,
    AnalysisResultRow,
    ArtifactRow,
    DownloadJobRow,
    MediaFormatRow,
    MediaInspectionRow,
    OutboxEventRow,
)
from .outbox_repository import SqlAlchemyDownloadRepository
from .session import create_engine, create_session_factory

__all__ = [
    "ArtifactCreate",
    "ArtifactRow",
    "ArtifactSnapshot",
    "AnalysisArtifactLockRow",
    "AnalysisJobRow",
    "AnalysisResultRow",
    "Base",
    "DownloadCreate",
    "DownloadJobRow",
    "FormatCreate",
    "FormatSnapshot",
    "IdempotencyConflict",
    "InspectionCreate",
    "InspectionCreateResult",
    "InspectionSnapshot",
    "JobCreateResult",
    "JobSnapshot",
    "JobSourceSnapshot",
    "LeaseConflict",
    "MediaFormatRow",
    "MediaInspectionRow",
    "OutboxEventRow",
    "OutboxSnapshot",
    "RepositoryConflict",
    "RepositoryError",
    "RepositoryNotFound",
    "SqlAlchemyDownloadRepository",
    "build_artifact_object_key",
    "create_engine",
    "create_session_factory",
]
