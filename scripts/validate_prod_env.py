from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_KEYS = [
    "APP_ENV",
    "CORS_ORIGINS",
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET_KEY",
    "REGISTRATION_ENABLED",
    "ADMIN_EMAILS",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "MINIO_ROOT_USER",
    "MINIO_ROOT_PASSWORD",
    "S3_ENDPOINT_URL",
    "S3_PUBLIC_ENDPOINT_URL",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_BUCKET",
    "WEB_API_BASE_URL",
]

UNSAFE_MARKERS = ("CHANGE_ME", "change-me", "your-domain.example")
LOCAL_HOSTS = {"127.0.0.1", "localhost", "0.0.0.0"}


def parse_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        env[key.strip()] = value
    return env


def fail(message: str) -> None:
    print(f"Production env validation failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def host_from_url(url: str) -> str:
    normalized = url
    if normalized.startswith("postgresql+psycopg://"):
        normalized = "postgresql://" + normalized.split("://", 1)[1]
    parsed = urlparse(normalized)
    return parsed.hostname or ""


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else ".env.production")
    if not path.exists():
        fail(f"{path} does not exist")

    env = parse_env(path)
    missing = [key for key in REQUIRED_KEYS if not env.get(key)]
    if missing:
        fail(f"missing required keys: {', '.join(missing)}")

    unsafe = [
        key
        for key in REQUIRED_KEYS
        if any(marker in env.get(key, "") for marker in UNSAFE_MARKERS)
    ]
    if unsafe:
        fail(f"replace placeholder values: {', '.join(unsafe)}")

    if env["APP_ENV"] != "production":
        fail("APP_ENV must be production")

    if len(env["JWT_SECRET_KEY"]) < 32:
        fail("JWT_SECRET_KEY must be at least 32 characters")

    if env["REGISTRATION_ENABLED"].lower() == "true" and not env.get("REGISTRATION_INVITE_CODE"):
        fail("public registration must use REGISTRATION_INVITE_CODE in production")

    for key in ("DATABASE_URL", "REDIS_URL", "S3_ENDPOINT_URL", "S3_PUBLIC_ENDPOINT_URL", "WEB_API_BASE_URL"):
        host = host_from_url(env[key])
        if host in LOCAL_HOSTS:
            fail(f"{key} must not point to {host} in production")

    if not re.match(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", env["S3_BUCKET"]):
        fail("S3_BUCKET must be a valid S3-compatible bucket name")

    print(f"Production env validation passed: {path}")


if __name__ == "__main__":
    main()
