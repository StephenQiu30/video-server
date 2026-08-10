from app.application.analysis.models import AnalysisSkillView
from app.application.analysis.ports import AnalysisSkillCatalog


class ListAnalysisSkills:
    def __init__(self, catalog: AnalysisSkillCatalog) -> None:
        self._catalog = catalog

    def __call__(self) -> tuple[AnalysisSkillView, ...]:
        return self._catalog.list()
