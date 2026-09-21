from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from app.services.provider_types import ProviderKey, ProviderSessionVersion
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.provider_cookie_file import ProviderCookieFile
from app.workers.runner.provider_session_bundle import (
    create_backup_key,
    decrypt_session_bundle,
    encrypt_session_bundle,
)
from app.workers.runner.provider_session_setup import publish_session

COOKIE = (
    b"# Netscape HTTP Cookie File\n"
    b".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tfixture-only\n"
)


def test_encrypted_bundle_restores_on_another_host_directory(tmp_path: Path) -> None:
    key = tmp_path / "separate" / "migration.key"
    bundle = tmp_path / "transfer" / "youtube.ffsession"
    destination = tmp_path / "machine-b" / "youtube"
    create_backup_key(key)

    encrypt_session_bundle(
        ProviderKey.YOUTUBE,
        COOKIE,
        key_file=key,
        destination=bundle,
    )
    restored = decrypt_session_bundle(
        ProviderKey.YOUTUBE,
        key_file=key,
        source=bundle,
    )
    publish_session(ProviderKey.YOUTUBE, destination, restored)

    assert stat.S_IMODE(key.stat().st_mode) == 0o600
    assert stat.S_IMODE(bundle.stat().st_mode) == 0o600
    assert (
        ProviderCookieFile(destination / "cookies.txt").read(
            ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER
        )
        == COOKIE
    )
    assert b"fixture-only" not in bundle.read_bytes()


def test_bundle_is_bound_to_provider(tmp_path: Path) -> None:
    key = tmp_path / "migration.key"
    bundle = tmp_path / "youtube.ffsession"
    create_backup_key(key)
    encrypt_session_bundle(
        ProviderKey.YOUTUBE,
        COOKIE,
        key_file=key,
        destination=bundle,
    )

    with pytest.raises(RunnerFailure) as caught:
        decrypt_session_bundle(
            ProviderKey.REDDIT,
            key_file=key,
            source=bundle,
        )

    assert caught.value.code == "credential_rejected"


def test_wrong_key_or_tampering_is_rejected(tmp_path: Path) -> None:
    key = tmp_path / "migration.key"
    wrong_key = tmp_path / "wrong.key"
    bundle = tmp_path / "youtube.ffsession"
    create_backup_key(key)
    create_backup_key(wrong_key)
    encrypt_session_bundle(
        ProviderKey.YOUTUBE,
        COOKIE,
        key_file=key,
        destination=bundle,
    )

    with pytest.raises(RunnerFailure):
        decrypt_session_bundle(
            ProviderKey.YOUTUBE,
            key_file=wrong_key,
            source=bundle,
        )

    document = json.loads(bundle.read_text())
    document["ciphertext"] = document["ciphertext"][:-2] + "AA"
    bundle.write_text(json.dumps(document))
    bundle.chmod(0o600)
    with pytest.raises(RunnerFailure):
        decrypt_session_bundle(
            ProviderKey.YOUTUBE,
            key_file=key,
            source=bundle,
        )


def test_backup_key_must_be_private_and_is_never_replaced(tmp_path: Path) -> None:
    key = tmp_path / "migration.key"
    create_backup_key(key)
    original = key.read_bytes()
    with pytest.raises(FileExistsError):
        create_backup_key(key)
    assert key.read_bytes() == original

    key.chmod(0o644)
    with pytest.raises(OSError):
        encrypt_session_bundle(
            ProviderKey.YOUTUBE,
            COOKIE,
            key_file=key,
            destination=tmp_path / "bundle.ffsession",
        )
