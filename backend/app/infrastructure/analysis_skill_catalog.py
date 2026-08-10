from app.analysis_skills import (
    BUILTIN_ANALYSIS_SKILLS,
    AnalysisSkill,
    AnalysisSkillRegistry,
)
from app.application.analysis.models import AnalysisSkillView


class BuiltinAnalysisSkillCatalog:
    def __init__(
        self, registry: AnalysisSkillRegistry = BUILTIN_ANALYSIS_SKILLS
    ) -> None:
        self._registry = registry

    def list(self) -> tuple[AnalysisSkillView, ...]:
        return tuple(_view(skill) for skill in self._registry.list())

    def resolve(self, skill_id: str) -> tuple[AnalysisSkillView, str] | None:
        skill = self._registry.get(skill_id)
        if skill is None:
            return None
        return _view(skill), skill.instructions


def _view(skill: AnalysisSkill) -> AnalysisSkillView:
    return AnalysisSkillView(
        id=skill.id,
        display_name=skill.display_name,
        description=skill.description,
        default_prompt=skill.default_prompt,
    )
