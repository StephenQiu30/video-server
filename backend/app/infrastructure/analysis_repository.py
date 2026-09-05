"""SQLAlchemy analysis port composed from independent repository capabilities."""

from .analysis_repository_create import AnalysisCreationRepository
from .analysis_repository_inputs import AnalysisInputRepository
from .analysis_repository_lifecycle import AnalysisLifecycleRepository
from .analysis_repository_publish import AnalysisPublishRepository
from .analysis_repository_recovery import AnalysisRecoveryRepository
from .analysis_repository_retry import AnalysisRetryRepository


class SqlAlchemyAnalysisRepository(
    AnalysisInputRepository,
    AnalysisCreationRepository,
    AnalysisRetryRepository,
    AnalysisLifecycleRepository,
    AnalysisRecoveryRepository,
    AnalysisPublishRepository,
):
    """Each capability shares sessions and helpers without inheriting siblings."""
