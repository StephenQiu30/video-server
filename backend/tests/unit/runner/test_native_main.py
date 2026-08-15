from pathlib import Path

import pytest
from app.runner import native_main
from app.runner.settings import RunnerSettings


def test_native_main_loads_runner_and_server_settings_from_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / "native.env"
    env_file.write_text(
        "\n".join(
            (
                f"RUNNER_HMAC_SECRET={'s' * 32}",
                "RUNNER_EGRESS_PROXY=http://127.0.0.1:13128",
                "NATIVE_RUNNER_HOST=::1",
                "NATIVE_RUNNER_PORT=19102",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NATIVE_RUNNER_ENV_FILE", str(env_file))
    captured: dict[str, object] = {}

    def fake_create_app(settings: RunnerSettings) -> RunnerSettings:
        captured["settings"] = settings
        return settings

    def fake_run(app: object, **kwargs: object) -> None:
        captured["app"] = app
        captured.update(kwargs)

    monkeypatch.setattr(native_main, "create_app", fake_create_app)
    monkeypatch.setattr(native_main.uvicorn, "run", fake_run)

    native_main.main()

    assert isinstance(captured["settings"], RunnerSettings)
    assert captured["app"] is captured["settings"]
    assert captured["host"] == "::1"
    assert captured["port"] == 19102
    assert captured["access_log"] is False
    assert captured["server_header"] is False


def test_native_main_rejects_symlinked_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.env"
    source.write_text("", encoding="utf-8")
    link = tmp_path / "native.env"
    link.symlink_to(source)
    monkeypatch.setenv("NATIVE_RUNNER_ENV_FILE", str(link))

    with pytest.raises(ValueError, match="regular file"):
        native_main.main()
