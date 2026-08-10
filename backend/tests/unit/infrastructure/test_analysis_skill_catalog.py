from pathlib import Path

import pytest
from app.analysis_skills import BUILTIN_ANALYSIS_SKILLS, AnalysisSkillRegistry
from app.infrastructure.analysis_skill_catalog import BuiltinAnalysisSkillCatalog


def test_builtin_skills_are_unversioned_and_director_breakdown_is_default() -> None:
    skills = BuiltinAnalysisSkillCatalog().list()

    assert skills[0].id == "director-breakdown"
    assert {skill.id for skill in skills} == {
        "director-breakdown",
        "comprehensive",
        "visual-shots",
        "highlights",
        "asset-catalog",
    }
    assert all(".v" not in skill.id for skill in skills)
    resolved = BuiltinAnalysisSkillCatalog().resolve("director-breakdown")
    assert resolved is not None
    assert "逐个观察视频中的真实 Cut" in resolved[1]


def test_registry_rejects_invalid_skill_documents(tmp_path: Path) -> None:
    skill_dir = tmp_path / "bad-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# missing metadata", encoding="utf-8")

    with pytest.raises(ValueError, match="frontmatter"):
        AnalysisSkillRegistry.from_directory(tmp_path)

    assert BUILTIN_ANALYSIS_SKILLS.get("missing") is None
