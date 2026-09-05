from __future__ import annotations

from typing import Any

import uvicorn
from app import main
from app.core.config import Settings


def test_run_uses_typed_host_and_port(monkeypatch: Any) -> None:
    settings = Settings(app_env="test", app_host="127.0.0.1", app_port=19191)
    captured: dict[str, Any] = {}

    def fake_run(target: str, **options: Any) -> None:
        captured.update(target=target, **options)

    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(uvicorn, "run", fake_run)

    main.run()

    assert captured == {
        "target": "app.main:app",
        "host": "127.0.0.1",
        "port": 19191,
        "reload": False,
        "proxy_headers": False,
    }
