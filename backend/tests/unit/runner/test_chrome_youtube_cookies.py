from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from app.runner import chrome_youtube_cookies as chrome


class _Decryptor:
    def __init__(self) -> None:
        self.values: list[bytes] = []

    def decrypt(self, value: bytes) -> str | None:
        self.values.append(value)
        if value == b"youtube-encrypted":
            return "youtube-value"
        raise AssertionError("a non-YouTube Cookie reached the decryptor")


def _database(path: Path, *, secure_column: str = "is_secure") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(
        f"""
        CREATE TABLE meta (
          key LONGVARCHAR NOT NULL UNIQUE PRIMARY KEY, value LONGVARCHAR
        );
        INSERT INTO meta VALUES ('version', '24');
        CREATE TABLE cookies (
          host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB, path TEXT,
          expires_utc INTEGER, {secure_column} INTEGER
        );
        """
    )
    connection.executemany(
        "INSERT INTO cookies VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            (".youtube.com", "session", "", b"youtube-encrypted", "/", 9, 1),
            ("embed.youtube-nocookie.com", "embed", "plain", b"", "/", 0, 1),
            ("accounts.google.com", "account", "", b"google-encrypted", "/", 9, 1),
            ("notyoutube.com", "other", "", b"other-encrypted", "/", 9, 1),
            ("youtube.com.attacker.test", "fake", "", b"fake-encrypted", "/", 9, 1),
        ),
    )
    connection.commit()
    connection.close()


def _profile(tmp_path: Path, name: str = "Default") -> tuple[Path, Path]:
    root = tmp_path / "Chrome"
    database = root / name / "Cookies"
    _database(database)
    return root, database


def _allow_macos(monkeypatch: pytest.MonkeyPatch, decryptor: _Decryptor) -> None:
    monkeypatch.setattr(chrome.sys, "platform", "darwin")
    monkeypatch.setattr(chrome, "_pinned_decryptor", lambda *args: decryptor)


def test_extract_selects_and_decrypts_only_youtube_rows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root, _ = _profile(tmp_path)
    decryptor = _Decryptor()
    _allow_macos(monkeypatch, decryptor)

    jar = chrome.extract_youtube_cookies(chrome_root=root)

    cookies = {(item.domain, item.name, item.value) for item in jar}
    assert cookies == {
        (".youtube.com", "session", "youtube-value"),
        ("embed.youtube-nocookie.com", "embed", "plain"),
    }
    assert decryptor.values == [b"youtube-encrypted"]


@pytest.mark.parametrize("profile", ("Default", "Profile 1", "Profile 42"))
def test_extract_accepts_only_named_chrome_profiles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile: str
) -> None:
    root, _ = _profile(tmp_path, profile)
    decryptor = _Decryptor()
    _allow_macos(monkeypatch, decryptor)

    assert len(chrome.extract_youtube_cookies(profile, chrome_root=root)) == 2


@pytest.mark.parametrize(
    "profile",
    ("", "Profile", "Profile 0", "../Default", "Default/../Profile 1", "/Default"),
)
def test_extract_rejects_unsafe_profile_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile: str
) -> None:
    root, _ = _profile(tmp_path)
    monkeypatch.setattr(chrome.sys, "platform", "darwin")

    with pytest.raises(ValueError, match="unsafe Chrome profile"):
        chrome.extract_youtube_cookies(profile, chrome_root=root)


def test_extract_reads_the_network_database_and_legacy_secure_column(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "Chrome"
    database = root / "Default" / "Network" / "Cookies"
    _database(database, secure_column="secure")
    decryptor = _Decryptor()
    _allow_macos(monkeypatch, decryptor)

    assert len(chrome.extract_youtube_cookies(chrome_root=root)) == 2


def test_extract_rejects_a_symlink_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root, database = _profile(tmp_path)
    actual = tmp_path / "actual"
    database.replace(actual)
    database.symlink_to(actual)
    monkeypatch.setattr(chrome.sys, "platform", "darwin")

    with pytest.raises(OSError, match="unsafe Chrome Cookie database"):
        chrome.extract_youtube_cookies(chrome_root=root)


def test_extract_rejects_a_non_regular_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "Chrome"
    database = root / "Default" / "Cookies"
    database.mkdir(parents=True)
    monkeypatch.setattr(chrome.sys, "platform", "darwin")

    with pytest.raises(OSError, match="unsafe Chrome Cookie database"):
        chrome.extract_youtube_cookies(chrome_root=root)


def test_extract_rejects_a_symlink_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root, _ = _profile(tmp_path, "Profile 1")
    (root / "Default").symlink_to(root / "Profile 1", target_is_directory=True)
    monkeypatch.setattr(chrome.sys, "platform", "darwin")

    with pytest.raises(OSError, match="unsafe Chrome profile"):
        chrome.extract_youtube_cookies(chrome_root=root)


def test_extract_reads_the_validated_database_without_a_disk_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root, source = _profile(tmp_path)
    decryptor = _Decryptor()
    opened: list[Path] = []
    original = chrome._read_filtered

    def inspect_source(database: Path, chrome_root: Path):  # type: ignore[no-untyped-def]
        opened.append(database)
        return original(database, chrome_root)

    _allow_macos(monkeypatch, decryptor)
    monkeypatch.setattr(chrome, "_read_filtered", inspect_source)

    chrome.extract_youtube_cookies(chrome_root=root)

    assert opened == [source]


def test_extract_is_macos_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root, _ = _profile(tmp_path)
    monkeypatch.setattr(chrome.sys, "platform", "linux")

    with pytest.raises(OSError, match="macOS"):
        chrome.extract_youtube_cookies(chrome_root=root)
