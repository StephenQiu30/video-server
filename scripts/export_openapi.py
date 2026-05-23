#!/usr/bin/env python
"""Export the FastAPI OpenAPI contract without starting the HTTP server."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "apps" / "worker"))
sys.path.insert(0, str(ROOT / "packages" / "shared"))

os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("SKIP_DB_BOOTSTRAP", "true")

from app.main import create_app  # noqa: E402


def export_openapi() -> dict:
    return create_app().openapi()


def main() -> int:
    payload = json.dumps(export_openapi(), ensure_ascii=False, indent=2)
    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1]).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
        print(f"Wrote OpenAPI contract to {output_path}")
        return 0

    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
