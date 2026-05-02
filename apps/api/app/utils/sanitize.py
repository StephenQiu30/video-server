from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_QUERY_KEYS = {"token", "signature", "auth", "cookie", "key", "access_token", "session"}


def redact_url(url: str) -> str:
    parts = urlsplit(url)
    safe_pairs = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        safe_pairs.append((key, "***" if key.lower() in SENSITIVE_QUERY_KEYS else value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(safe_pairs), parts.fragment))


def safe_filename(name: str, fallback: str = "video") -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in name).strip()
    cleaned = cleaned.replace("/", "_").replace("\\", "_")
    cleaned = cleaned[:180].strip(" .")
    return cleaned or fallback


def ensure_child_path(base_dir: str, path: str) -> Path:
    base = Path(base_dir).resolve()
    candidate = Path(path).resolve()
    if base != candidate and base not in candidate.parents:
        raise ValueError("path escapes controlled download directory")
    return candidate

