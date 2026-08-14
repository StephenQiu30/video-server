from __future__ import annotations

from pathlib import Path

import pytest
from app.analysis_skills import BUILTIN_ANALYSIS_SKILLS, AnalysisSkillRegistry
from app.domain.analysis import AnalysisInputKind, AnalysisResultContract
from app.infrastructure.analysis_skill_catalog import BuiltinAnalysisSkillCatalog


def _document(
    name: str,
    *,
    input_kind: str = "video",
    contract: str = "video-visual-analysis",
    extra_top: str = "",
    extra_metadata: str = "",
    references: str = "",
) -> str:
    return f"""---
name: {name}
description: Test skill for validating analysis registry behavior.
license: MIT
{extra_top}metadata:
  video-server-display-name: Test Skill
  video-server-default-prompt: Analyze the supplied input.
  video-server-order: "10"
  video-server-input-kinds: {input_kind}
  video-server-output-contract: {contract}
{extra_metadata}{references}---

# Test

Use only supplied evidence.
"""


def _write_skill(root: Path, name: str, document: str | None = None) -> Path:
    skill_dir = root / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(document or _document(name), encoding="utf-8")
    return skill_dir


def test_builtin_skills_are_filtered_ordered_and_contract_bound() -> None:
    catalog = BuiltinAnalysisSkillCatalog()

    video = catalog.list(AnalysisInputKind.VIDEO)
    screenplay = catalog.list(AnalysisInputKind.SCREENPLAY)

    assert [skill.id for skill in video] == [
        "director-breakdown",
        "comprehensive",
        "visual-shots",
        "highlights",
        "asset-catalog",
    ]
    assert [skill.id for skill in screenplay] == [
        "screenplay-analysis",
        "screenplay-structure-review",
        "screenplay-rewrite",
    ]
    assert {skill.result_contract for skill in video} == {
        AnalysisResultContract.VIDEO_VISUAL_ANALYSIS
    }
    assert [skill.result_contract for skill in screenplay] == [
        AnalysisResultContract.SCREENPLAY_ANALYSIS,
        AnalysisResultContract.SCREENPLAY_ANALYSIS,
        AnalysisResultContract.SCREENPLAY_REWRITE,
    ]


def test_builtin_resolution_compiles_allowlisted_reference_and_sha256() -> None:
    catalog = BuiltinAnalysisSkillCatalog()

    resolved = catalog.resolve("screenplay-analysis", AnalysisInputKind.SCREENPLAY)

    assert resolved is not None
    assert "# Reference: references/evidence-rules.md" in resolved.instructions
    assert len(resolved.instructions_sha256) == 64
    assert catalog.resolve("screenplay-analysis", AnalysisInputKind.VIDEO) is None
    assert BUILTIN_ANALYSIS_SKILLS.get("missing", AnalysisInputKind.VIDEO) is None


@pytest.mark.parametrize(
    ("document", "message"),
    (
        ("# missing metadata", "frontmatter"),
        (_document("Bad-Skill"), "skill id"),
        (
            _document("bad-skill", extra_top="allowed-tools: Bash\n"),
            "frontmatter field",
        ),
        (
            _document("bad-skill", extra_metadata="  video-server-unknown: value\n"),
            "product metadata",
        ),
        (_document("bad-skill", input_kind="audio"), "input kind"),
        (_document("bad-skill", contract="unknown"), "result contract"),
        (
            _document("bad-skill", input_kind="screenplay"),
            "incompatible",
        ),
        (
            _document(
                "bad-skill",
                references="  video-server-references: ../outside.md\n",
            ),
            "unsafe",
        ),
        (
            _document(
                "bad-skill",
                references="  video-server-references: /absolute.md\n",
            ),
            "unsafe",
        ),
    ),
)
def test_registry_rejects_invalid_skill_contracts(
    tmp_path: Path, document: str, message: str
) -> None:
    _write_skill(tmp_path, "bad-skill", document)

    with pytest.raises(ValueError, match=message):
        AnalysisSkillRegistry.from_directory(tmp_path)


def test_registry_rejects_unlisted_references_and_executable_resources(
    tmp_path: Path,
) -> None:
    skill_dir = _write_skill(tmp_path, "bad-skill")
    references = skill_dir / "references"
    references.mkdir()
    (references / "hidden.md").write_text("hidden", encoding="utf-8")

    with pytest.raises(ValueError, match="unlisted"):
        AnalysisSkillRegistry.from_directory(tmp_path)

    references.rename(skill_dir / "scripts")
    with pytest.raises(ValueError, match="unsupported"):
        AnalysisSkillRegistry.from_directory(tmp_path)


def test_registry_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    document = _document("bad-skill").replace(
        "name: bad-skill", "name: bad-skill\nname: bad-skill"
    )
    _write_skill(tmp_path, "bad-skill", document)

    with pytest.raises(ValueError, match="YAML"):
        AnalysisSkillRegistry.from_directory(tmp_path)


def test_registry_rejects_duplicate_ids() -> None:
    skill = BUILTIN_ANALYSIS_SKILLS.get("director-breakdown", AnalysisInputKind.VIDEO)
    assert skill is not None

    with pytest.raises(ValueError, match="duplicate"):
        AnalysisSkillRegistry((skill, skill))


def test_registry_rejects_skill_directory_symlinks(tmp_path: Path) -> None:
    target = tmp_path / "outside"
    target.mkdir()
    _write_skill(target, "linked-skill")
    link = tmp_path / "linked-skill"
    try:
        link.symlink_to(target / "linked-skill", target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable on this platform")

    with pytest.raises(ValueError, match="symlink"):
        AnalysisSkillRegistry.from_directory(tmp_path)


def test_registry_rejects_reference_symlinks(tmp_path: Path) -> None:
    document = _document(
        "linked-reference",
        references="  video-server-references: references/rules.md\n",
    )
    skill_dir = _write_skill(tmp_path, "linked-reference", document)
    references = skill_dir / "references"
    references.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    try:
        (references / "rules.md").symlink_to(outside)
    except OSError:
        pytest.skip("file symlinks are unavailable on this platform")

    with pytest.raises(ValueError, match="missing analysis skill reference"):
        AnalysisSkillRegistry.from_directory(tmp_path)
