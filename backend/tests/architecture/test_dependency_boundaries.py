from __future__ import annotations

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "app"

OUTER_APP_LAYERS = (
    "app.api",
    "app.infrastructure",
    "app.runner",
    "app.workers",
)
INFRASTRUCTURE_PACKAGES = (
    "aio_pika",
    "fastapi",
    "langchain",
    "minio",
    "openai",
    "sqlalchemy",
    "yt_dlp",
)


def test_domain_and_application_only_depend_inward() -> None:
    rules = {
        APP_ROOT / "domain": (
            "app.application",
            *OUTER_APP_LAYERS,
            *INFRASTRUCTURE_PACKAGES,
        ),
        APP_ROOT / "application": (
            *OUTER_APP_LAYERS,
            *INFRASTRUCTURE_PACKAGES,
        ),
    }
    violations: list[str] = []

    for layer, forbidden_prefixes in rules.items():
        for source in layer.rglob("*.py"):
            for imported in _imported_modules(source):
                if any(_matches(imported, prefix) for prefix in forbidden_prefixes):
                    violations.append(
                        f"{source.relative_to(APP_ROOT)} imports {imported}"
                    )

    assert not violations, "Invalid outward dependencies:\n" + "\n".join(violations)


def _imported_modules(source: Path) -> set[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _matches(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")
