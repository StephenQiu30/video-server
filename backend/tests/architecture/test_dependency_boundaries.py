from __future__ import annotations

import ast
from importlib.util import resolve_name
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "app"

OUTER_APP_LAYERS = (
    "app.api",
    "app.main",
    "app.integrations",
    "app.repositories",
    "app.core.db",
    "app.models",
    "app.schemas",
    "app.core.runtime",
    "app.core.composition",
    "app.core.lifespan",
    "app.workers",
)
INFRASTRUCTURE_PACKAGES = (
    "aio_pika",
    "fastapi",
    "minio",
    "sqlalchemy",
    "yt_dlp",
)


def test_business_logic_is_independent_of_http_and_io() -> None:
    for source in (APP_ROOT / "services").rglob("*.py"):
        for module in _imported_modules(source):
            assert not any(
                _matches(module, prefix)
                for prefix in (*OUTER_APP_LAYERS, *INFRASTRUCTURE_PACKAGES)
            ), f"{source.relative_to(APP_ROOT)} imports {module}"


def test_fastapi_layout_and_route_dependencies() -> None:
    directories = {
        p.name for p in APP_ROOT.iterdir() if p.is_dir() and p.name != "__pycache__"
    }
    assert directories == {
        "api",
        "core",
        "repositories",
        "models",
        "schemas",
        "services",
        "integrations",
        "workers",
    }
    assert {p.name for p in APP_ROOT.glob("*.py")} == {"__init__.py", "main.py"}
    assert (APP_ROOT / "api/deps.py").is_file()
    sources = list((APP_ROOT / "api/routes").glob("*.py"))
    assert sources
    for source in sources:
        assert not any(
            _matches(module, "app.main") for module in _imported_modules(source)
        ), f"Router imports the application entry: {source.name}"


def _imported_modules(source: Path) -> set[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = source.parent.relative_to(APP_ROOT.parent).as_posix()
                module = resolve_name(
                    "." * node.level + (node.module or ""), package.replace("/", ".")
                )
            else:
                module = node.module or ""
            modules.add(module)
            modules.update(f"{module}.{name.name}" for name in node.names)
    return modules


def _matches(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def test_database_and_models_do_not_import_services_or_adapters() -> None:
    forbidden = (
        "app.api",
        "app.repositories",
        "app.integrations",
        "app.workers",
        "app.main",
        "app.core.runtime",
        "app.core.composition",
    )
    sources = [APP_ROOT / "core/db.py", *(APP_ROOT / "models").rglob("*.py")]
    for source in sources:
        assert source.is_file()
        for module in _imported_modules(source):
            assert not any(_matches(module, prefix) for prefix in forbidden), (
                f"{source.relative_to(APP_ROOT)} imports {module}"
            )
