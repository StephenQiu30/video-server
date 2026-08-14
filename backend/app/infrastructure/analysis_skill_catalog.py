from app.analysis_skills import (
    BUILTIN_ANALYSIS_SKILLS,
    AnalysisSkill,
    AnalysisSkillRegistry,
)
from app.application.analysis.models import AnalysisSkillResolution, AnalysisSkillView
from app.domain.analysis import AnalysisInputKind


class BuiltinAnalysisSkillCatalog:
    def __init__(
        self, registry: AnalysisSkillRegistry = BUILTIN_ANALYSIS_SKILLS
    ) -> None:
        self._registry = registry

    def list(self, input_kind: AnalysisInputKind) -> tuple[AnalysisSkillView, ...]:
        return tuple(_view(skill) for skill in self._registry.list(input_kind))

    def resolve(
        self, skill_id: str, input_kind: AnalysisInputKind
    ) -> AnalysisSkillResolution | None:
        skill = self._registry.get(skill_id, input_kind)
        if skill is None:
            return None
        return AnalysisSkillResolution(
            view=_view(skill),
            instructions=skill.instructions,
            instructions_sha256=skill.instructions_sha256,
        )


def _view(skill: AnalysisSkill) -> AnalysisSkillView:
    return AnalysisSkillView(
        id=skill.id,
        display_name=skill.display_name,
        description=skill.description,
        default_prompt=skill.default_prompt,
        input_kinds=skill.input_kinds,
        result_contract=skill.result_contract,
    )
