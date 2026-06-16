"""Architecture boundary tests for the FastAPI backend.

These tests enforce the layered dependency constraints defined in
PRD08 and PLAN13 to prevent cross-layer coupling regression.
"""

import ast
from pathlib import Path

ROUTER_DIR = Path("apps/api/app/routers")
SERVICE_DIR = Path("apps/api/app/services")
CORE_DIR = Path("apps/api/app/core")

# External SDKs that router must NOT import directly
FORBIDDEN_ROUTER_IMPORTS = {
    "yt_dlp",
    "minio",
    "rq",
    "celery",
}


def _collect_imports_from_file(filepath: Path) -> set[str]:
    """Collect all import targets from a Python file using AST."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    imports.add(f"{node.module}.{alias.name}")
    return imports


def _collect_import_modules_from_file(filepath: Path) -> set[str]:
    """Collect top-level module names from import statements."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split(".")[0])
    return modules


def test_router_does_not_import_ytdlp_directly() -> None:
    """Router layer SHALL NOT import yt_dlp directly."""
    for py_file in ROUTER_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        imports = _collect_import_modules_from_file(py_file)
        assert "yt_dlp" not in imports, (
            f"{py_file} imports yt_dlp directly. "
            "Router should access yt-dlp through service/adapter layer."
        )


def test_router_does_not_import_minio_directly() -> None:
    """Router layer SHALL NOT import minio directly."""
    for py_file in ROUTER_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        imports = _collect_import_modules_from_file(py_file)
        assert "minio" not in imports, (
            f"{py_file} imports minio directly. "
            "Router should access storage through service layer."
        )


def test_router_does_not_import_rq_or_celery_directly() -> None:
    """Router layer SHALL NOT import rq or celery directly.

    Exception: health.py is allowed to import rq/redis for infrastructure
    health checks (readiness probes), as this is not business logic.
    """
    # Health endpoints are infrastructure concerns, not business logic
    health_exceptions = {"health.py"}
    for py_file in ROUTER_DIR.glob("*.py"):
        if py_file.name == "__init__.py" or py_file.name in health_exceptions:
            continue
        imports = _collect_import_modules_from_file(py_file)
        for forbidden in ("rq", "celery"):
            assert forbidden not in imports, (
                f"{py_file} imports {forbidden} directly. "
                "Router should access task queue through service layer."
            )


def test_service_does_not_import_from_router() -> None:
    """Service layer SHALL NOT import from router layer."""
    for py_file in SERVICE_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("app.routers"):
                    raise AssertionError(
                        f"{py_file} imports from app.routers. "
                        "Service layer should not depend on router layer."
                    )


def test_core_does_not_import_from_service_or_router() -> None:
    """Core layer SHALL NOT import from service or router layers."""
    for py_file in CORE_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and (
                    node.module.startswith("app.services")
                    or node.module.startswith("app.routers")
                ):
                    raise AssertionError(
                        f"{py_file} imports from {node.module}. "
                        "Core layer should not depend on service or router layers."
                    )


def test_task_state_has_single_source_of_truth() -> None:
    """TaskState MUST be imported from video_downloader_shared.states."""
    for directory in [ROUTER_DIR, SERVICE_DIR]:
        for py_file in directory.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "states" in node.module:
                        assert "video_downloader_shared" in node.module, (
                            f"{py_file} imports TaskState from {node.module}. "
                            "TaskState should be imported from video_downloader_shared.states."
                        )


def test_error_code_has_single_source_of_truth() -> None:
    """ErrorCode MUST be imported from app.core.errors."""
    for directory in [ROUTER_DIR, SERVICE_DIR]:
        for py_file in directory.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "errors" in node.module:
                        assert node.module == "app.core.errors", (
                            f"{py_file} imports ErrorCode from {node.module}. "
                            "ErrorCode should be imported from app.core.errors."
                        )


def test_prd08_document_exists() -> None:
    """PRD08 document MUST exist for backend architecture governance."""
    prd_path = Path("docs/prd/08-后端工程规范与架构治理.md")
    assert prd_path.exists(), "PRD08 document is missing"


def test_plan13_document_exists() -> None:
    """PLAN13 document MUST exist for backend architecture governance."""
    plan_path = Path("docs/plans/13-后端工程规范与架构治理计划.md")
    assert plan_path.exists(), "PLAN13 document is missing"


def test_openspec_backend_layer_boundaries_spec_exists() -> None:
    """OpenSpec backend-layer-boundaries spec MUST exist."""
    spec_path = Path("openspec/specs/backend-layer-boundaries/spec.md")
    assert spec_path.exists(), "OpenSpec backend-layer-boundaries spec is missing"
