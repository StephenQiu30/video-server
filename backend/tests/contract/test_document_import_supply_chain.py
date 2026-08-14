from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_document_import_sbom_pins_versions_and_licenses() -> None:
    document = json.loads(
        (ROOT / "config/document-import-sbom.json").read_text(encoding="utf-8")
    )
    components = {item["name"]: item for item in document["components"]}

    assert document["bomFormat"] == "CycloneDX"
    assert components["python-docx"]["version"] == "1.2.0"
    assert components["markdown-it-py"]["version"] == "4.2.0"
    assert components["pypdf"]["version"] == "6.16.0"
    assert components["pypdf"]["properties"][0]["value"] == (
        "2b60c99973df8d7f959cd46658604d881be3de3a"
    )
    assert all(component.get("licenses") for component in components.values())


def test_pdf_dependency_and_notices_are_shipped_with_the_runtime() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    dockerfile = (ROOT.parent / "Dockerfile").read_text(encoding="utf-8")
    notices = (ROOT / "config/DOCUMENT-IMPORT-NOTICES.md").read_text(encoding="utf-8")

    assert '"pypdf==6.16.0"' in pyproject
    assert "config/document-import-sbom.json" in dockerfile
    assert "config/DOCUMENT-IMPORT-NOTICES.md" in dockerfile
    assert "BSD-3-Clause" in notices
    assert "OCR is not included" in notices
