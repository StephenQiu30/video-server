"""Read only YouTube cookies from one local macOS Chrome profile."""

from __future__ import annotations

import re
import sqlite3
import stat
import sys
from http.cookiejar import Cookie, CookieJar
from pathlib import Path
from typing import Protocol, cast

from yt_dlp import cookies as yt_dlp_cookies  # type: ignore[import-untyped]

DEFAULT_CHROME_ROOT = (
    Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
)
_PROFILE = re.compile(r"(?:Default|Profile [1-9][0-9]*)")
_DOMAINS = ("youtube.com", "youtube-nocookie.com")
_COOKIE_QUERY = """
SELECT host_key, name, value, encrypted_value, path, expires_utc, {secure}
FROM cookies
WHERE lower(ltrim(host_key, '.')) = ?
   OR lower(ltrim(host_key, '.')) LIKE '%.' || ?
   OR lower(ltrim(host_key, '.')) = ?
   OR lower(ltrim(host_key, '.')) LIKE '%.' || ?
"""


class _CookieDecryptor(Protocol):
    def decrypt(self, encrypted_value: bytes) -> str | None: ...


class _SilentLogger:
    def _ignore(self, *args: object, **kwargs: object) -> None:
        pass

    debug = info = warning = error = _ignore


def extract_youtube_cookies(
    profile: str = "Default",
    *,
    chrome_root: Path = DEFAULT_CHROME_ROOT,
) -> CookieJar:
    """Return a jar populated only by the allowlisted Chrome Cookie rows."""
    if sys.platform != "darwin":
        raise OSError("macOS Chrome Cookie extraction is unavailable")
    profile_dir = _safe_profile(chrome_root, profile)
    database = _cookie_database(profile_dir)
    return _read_filtered(database, chrome_root)


def _safe_profile(chrome_root: Path, profile: str) -> Path:
    if _PROFILE.fullmatch(profile) is None:
        raise ValueError("unsafe Chrome profile name")
    _require_directory(chrome_root)
    profile_dir = chrome_root / profile
    _require_directory(profile_dir)
    return profile_dir


def _cookie_database(profile_dir: Path) -> Path:
    candidates: list[tuple[int, Path]] = []
    network = profile_dir / "Network"
    if _lexists(network):
        _require_directory(network)
    for candidate in (profile_dir / "Cookies", network / "Cookies"):
        if not _lexists(candidate):
            continue
        info = candidate.lstat()
        if candidate.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise OSError("unsafe Chrome Cookie database")
        candidates.append((info.st_mtime_ns, candidate))
    if not candidates:
        raise FileNotFoundError("Chrome Cookie database was not found")
    return max(candidates, key=lambda item: item[0])[1]


def _read_filtered(database: Path, chrome_root: Path) -> CookieJar:
    before = database.lstat()
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    try:
        current = database.lstat()
        if (
            database.is_symlink()
            or not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise OSError("unsafe Chrome Cookie database")
        connection.execute("PRAGMA query_only = ON")
        meta_row = connection.execute(
            "SELECT value FROM meta WHERE key = 'version'"
        ).fetchone()
        meta_version = int(meta_row[0]) if meta_row else 0
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(cookies)")
        }
        secure = "is_secure" if "is_secure" in columns else "secure"
        if secure not in columns:
            raise sqlite3.DatabaseError("unsupported Chrome Cookie schema")
        connection.text_factory = bytes
        rows = connection.execute(
            _COOKIE_QUERY.format(secure=secure),
            (_DOMAINS[0], _DOMAINS[0], _DOMAINS[1], _DOMAINS[1]),
        )
        decryptor = _pinned_decryptor(chrome_root, meta_version)
        jar = CookieJar()
        for row in rows:
            cookie = _to_cookie(decryptor, row)
            if cookie is not None:
                jar.set_cookie(cookie)
        return jar
    finally:
        connection.close()


def _pinned_decryptor(chrome_root: Path, meta_version: int) -> _CookieDecryptor:
    """Narrow compatibility boundary for the commit-pinned yt-dlp package."""
    factory = getattr(yt_dlp_cookies, "get_cookie_decryptor", None)
    if not callable(factory):
        raise RuntimeError("pinned yt-dlp Cookie decryptor is unavailable")
    return cast(
        _CookieDecryptor,
        factory(str(chrome_root), "Chrome", _SilentLogger(), meta_version=meta_version),
    )


def _to_cookie(decryptor: _CookieDecryptor, row: tuple[object, ...]) -> Cookie | None:
    host, name, value, encrypted, path, expires, secure = row
    try:
        decoded_value = cast(bytes, value).decode()
        if not decoded_value and encrypted:
            decrypted = decryptor.decrypt(cast(bytes, encrypted))
            if decrypted is None:
                return None
            decoded_value = decrypted
        decoded_host = cast(bytes, host).decode()
        decoded_name = cast(bytes, name).decode()
        decoded_path = cast(bytes, path).decode()
    except Exception:
        return None
    expiry = int(cast(int, expires)) or None
    return Cookie(
        0,
        decoded_name,
        decoded_value,
        None,
        False,
        decoded_host,
        bool(decoded_host),
        decoded_host.startswith("."),
        decoded_path,
        bool(decoded_path),
        bool(secure),
        expiry,
        expiry is None,
        None,
        None,
        {},
        False,
    )


def _require_directory(path: Path) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise OSError("unsafe Chrome profile path")


def _lexists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True
