from app.services.analysis.models import AnalysisSkillView
from app.services.analysis.ports import AnalysisSkillCatalog
from app.services.analysis.rules.enums import AnalysisInputKind


class ListAnalysisSkills:
    def __init__(self, catalog: AnalysisSkillCatalog) -> None:
        self._catalog = catalog

    def __call__(self, input_kind: AnalysisInputKind) -> tuple[AnalysisSkillView, ...]:
        return self._catalog.list(input_kind)
