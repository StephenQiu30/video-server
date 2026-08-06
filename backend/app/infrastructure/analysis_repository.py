"""Concrete SQLAlchemy adapter for the analysis application repository port."""

from app.infrastructure.analysis_repository_publish import AnalysisPublishRepository


class SqlAlchemyAnalysisRepository(AnalysisPublishRepository):
    pass
