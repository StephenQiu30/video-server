from __future__ import annotations

_PROFILE = "video_analysis"


def codex_permission_arguments() -> tuple[str, ...]:
    return (
        "-c",
        f'default_permissions="{_PROFILE}"',
        "-c",
        f"permissions.{_PROFILE}.filesystem={_filesystem_value()}",
        "-c",
        f"permissions.{_PROFILE}.network.enabled=false",
        # Disable the codex sandbox entirely: on Windows its Docker/WSL2 backend
        # intermittently fails to initialize or blocks host tools (ffmpeg/ffprobe),
        # producing degraded placeholder analyses. The worker already runs on the
        # host with full filesystem access, so the sandbox adds no security.
        "-c",
        'sandbox_mode="danger-full-access"',
    )


def _filesystem_value() -> str:
    return (
        '{":minimal"="read",'
        '":workspace_roots"={"."="read",work="write",'
        'output="write",tmp="write"}}'
    )
