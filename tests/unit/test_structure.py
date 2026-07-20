from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_source_is_directly_under_src_without_wrapper_package() -> None:
    assert (ROOT / "src" / "main.py").is_file()
    assert (ROOT / "src" / "core" / "config.py").is_file()
    assert not (ROOT / "src" / "video_server").exists()


def test_forbidden_optional_infrastructure_is_not_declared() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for forbidden in ("celery", "redis", "cobalt", "metube"):
        assert forbidden not in pyproject.lower()
