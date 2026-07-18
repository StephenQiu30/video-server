from __future__ import annotations

import os
from pathlib import Path

import pytest

from video_server.config import validate_bind_host
from video_server.errors import DomainError
from video_server.security.secrets import load_secret_bytes, load_secret_text


def _write_secret(path: Path, data: bytes, *, mode: int = 0o600) -> Path:
    path.write_bytes(data)
    path.chmod(mode)
    return path


def _assert_bind_rejected(host: str, *, provider: bool = False) -> None:
    with pytest.raises((DomainError, ValueError)) as error:
        validate_bind_host(host, principal_provider_configured=provider)

    assert str(error.value)
    if isinstance(error.value, DomainError):
        assert error.value.code
        assert error.value.detail


@pytest.mark.security
def test_byte_secret_preserves_exact_bytes_and_enforces_exact_size(tmp_path: Path) -> None:
    secret = b"\x00  raw-secret\n\xff"
    path = _write_secret(tmp_path / "key.bin", secret)

    assert load_secret_bytes(path, expected_size=len(secret)) == secret


@pytest.mark.security
def test_text_secret_accepts_owner_read_only_file_without_trimming(tmp_path: Path) -> None:
    text = " 令牌 e\u0301 \n"
    path = _write_secret(tmp_path / "token", text.encode(), mode=0o400)

    assert load_secret_text(path) == text


@pytest.mark.security
@pytest.mark.parametrize("expected_size", [3, 5])
def test_byte_secret_rejects_any_size_mismatch(
    tmp_path: Path,
    expected_size: int,
) -> None:
    path = _write_secret(tmp_path / "key.bin", b"1234")

    with pytest.raises(ValueError):
        load_secret_bytes(path, expected_size=expected_size)


@pytest.mark.security
def test_secret_loaders_reject_empty_material(tmp_path: Path) -> None:
    path = _write_secret(tmp_path / "empty", b"")

    with pytest.raises(ValueError):
        load_secret_bytes(path)
    with pytest.raises(ValueError):
        load_secret_text(path)


@pytest.mark.security
def test_text_secret_rejects_invalid_utf8(tmp_path: Path) -> None:
    path = _write_secret(tmp_path / "token", b"valid-prefix\xff")

    with pytest.raises((UnicodeError, ValueError)):
        load_secret_text(path)


@pytest.mark.security
@pytest.mark.parametrize("mode", [0o640, 0o604])
def test_secret_rejects_every_group_or_other_permission(
    tmp_path: Path,
    mode: int,
) -> None:
    path = _write_secret(tmp_path / f"secret-{mode:o}", b"secret", mode=mode)

    with pytest.raises(ValueError):
        load_secret_bytes(path)


@pytest.mark.security
def test_secret_rejects_directory_and_symlink_even_to_valid_file(tmp_path: Path) -> None:
    target = _write_secret(tmp_path / "target", b"secret")
    link = tmp_path / "link"
    link.symlink_to(target)
    directory = tmp_path / "directory"
    directory.mkdir(mode=0o700)

    with pytest.raises(ValueError):
        load_secret_bytes(link)
    with pytest.raises(ValueError):
        load_secret_bytes(directory)


@pytest.mark.security
def test_secret_rejects_file_not_owned_by_current_user(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_secret(tmp_path / "foreign", b"secret")
    other_uid = path.stat().st_uid + 1
    monkeypatch.setattr(os, "getuid", lambda: other_uid)
    monkeypatch.setattr(os, "geteuid", lambda: other_uid)

    with pytest.raises(ValueError):
        load_secret_bytes(path)


@pytest.mark.security
@pytest.mark.parametrize(
    ("host", "canonical"),
    [
        ("localhost", "localhost"),
        ("127.0.0.1", "127.0.0.1"),
        ("127.200.10.4", "127.200.10.4"),
        ("::1", "::1"),
        ("0:0:0:0:0:0:0:1", "::1"),
    ],
)
def test_bind_host_accepts_and_canonicalizes_loopback(
    host: str,
    canonical: str,
) -> None:
    assert validate_bind_host(host, principal_provider_configured=False) == canonical


@pytest.mark.security
@pytest.mark.parametrize(
    "host",
    ["", "*", "0.0.0.0", "::", "192.168.1.10", "api.example"],
)
def test_bind_host_fails_closed_without_principal_provider(host: str) -> None:
    _assert_bind_rejected(host)


@pytest.mark.security
@pytest.mark.parametrize(
    ("host", "canonical"),
    [("0.0.0.0", "0.0.0.0"), ("::", "::"), ("API.Example.", "api.example")],
)
def test_bind_host_allows_canonical_non_loopback_with_principal_provider(
    host: str,
    canonical: str,
) -> None:
    assert validate_bind_host(host, principal_provider_configured=True) == canonical


@pytest.mark.security
def test_bind_host_rejects_empty_value_even_with_principal_provider() -> None:
    _assert_bind_rejected("", provider=True)
