from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_SKILL_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class AnalysisSkill:
    id: str
    display_name: str
    description: str
    default_prompt: str
    instructions: str
    order: int


class AnalysisSkillRegistry:
    def __init__(self, skills: tuple[AnalysisSkill, ...]) -> None:
        if not skills:
            raise ValueError("at least one analysis skill is required")
        by_id: dict[str, AnalysisSkill] = {}
        for skill in skills:
            if skill.id in by_id:
                raise ValueError(f"duplicate analysis skill: {skill.id}")
            by_id[skill.id] = skill
        self._skills = tuple(sorted(skills, key=lambda item: (item.order, item.id)))
        self._by_id = by_id

    @classmethod
    def from_directory(cls, root: Path) -> AnalysisSkillRegistry:
        return cls(tuple(_load_skill(path) for path in root.glob("*/SKILL.md")))

    def list(self) -> tuple[AnalysisSkill, ...]:
        return self._skills

    def get(self, skill_id: str) -> AnalysisSkill | None:
        return self._by_id.get(skill_id)


def _load_skill(path: Path) -> AnalysisSkill:
    document = path.read_text(encoding="utf-8")
    if not document.startswith("---\n") or "\n---\n" not in document[4:]:
        raise ValueError(f"invalid analysis skill frontmatter: {path}")
    raw_metadata, instructions = document[4:].split("\n---\n", 1)
    metadata: dict[str, str] = {}
    for line in raw_metadata.splitlines():
        key, separator, value = line.partition(":")
        if not separator or not key.strip() or not value.strip():
            raise ValueError(f"invalid analysis skill metadata: {path}")
        metadata[key.strip()] = value.strip()
    required = {"name", "display_name", "description", "default_prompt", "order"}
    if set(metadata) != required:
        raise ValueError(f"incomplete analysis skill metadata: {path}")
    skill_id = metadata["name"]
    if skill_id != path.parent.name or _SKILL_ID.fullmatch(skill_id) is None:
        raise ValueError(f"invalid analysis skill id: {path}")
    normalized_instructions = instructions.strip()
    if not normalized_instructions:
        raise ValueError(f"analysis skill instructions cannot be blank: {path}")
    return AnalysisSkill(
        id=skill_id,
        display_name=metadata["display_name"],
        description=metadata["description"],
        default_prompt=metadata["default_prompt"],
        instructions=normalized_instructions,
        order=int(metadata["order"]),
    )


BUILTIN_ANALYSIS_SKILLS = AnalysisSkillRegistry.from_directory(_ROOT)
