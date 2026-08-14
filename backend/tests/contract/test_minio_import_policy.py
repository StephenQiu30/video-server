from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INIT_SCRIPT = ROOT / "config" / "minio" / "init.sh"
COMPOSE = ROOT.parent / "docker-compose.yml"
PROD_COMPOSE = ROOT.parent / "docker-compose-prod.yml"


def test_import_identity_is_separate_and_quarantine_scoped() -> None:
    script = INIT_SCRIPT.read_text(encoding="utf-8")
    policy = _json_document(script, "import-policy.json").replace(
        "$bucket", "arn:aws:s3:::video-artifacts"
    )
    statements = json.loads(policy)["Statement"]
    object_resources = {
        resource
        for statement in statements
        for resource in statement["Resource"]
        if resource != "arn:aws:s3:::video-artifacts"
    }

    assert "arn:aws:s3:::video-artifacts/quarantine/*" in object_resources
    assert "arn:aws:s3:::video-artifacts/downloads/*" in object_resources
    assert "arn:aws:s3:::video-artifacts/documents/*" in object_resources
    assert all(
        resource.startswith(
            (
                "arn:aws:s3:::video-artifacts/quarantine/",
                "arn:aws:s3:::video-artifacts/downloads/",
                "arn:aws:s3:::video-artifacts/documents/",
            )
        )
        for resource in object_resources
    )
    assert 'create_role "$MINIO_IMPORT_ACCESS_KEY"' in script


def test_public_api_and_analysis_policies_cannot_read_quarantine() -> None:
    script = INIT_SCRIPT.read_text(encoding="utf-8")

    for document in ("api-policy.json", "analysis-policy.json"):
        policy = _json_document(script, document)
        assert "quarantine" not in policy


def test_quarantine_lifecycle_expires_objects_and_incomplete_uploads() -> None:
    script = INIT_SCRIPT.read_text(encoding="utf-8")
    lifecycle = json.loads(
        _json_document(script, "lifecycle.json").replace(
            "$IMPORT_QUARANTINE_RETENTION_DAYS", "1"
        )
    )

    assert lifecycle == {
        "Rules": [
            {
                "ID": "quarantine-expiry-v1",
                "Status": "Enabled",
                "Filter": {"Prefix": "quarantine/"},
                "Expiration": {"Days": 1},
                "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
            }
        ]
    }


def test_compose_requires_import_credentials_in_production() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    production = PROD_COMPOSE.read_text(encoding="utf-8")

    for variable in (
        "MINIO_IMPORT_ACCESS_KEY",
        "MINIO_IMPORT_SECRET_KEY",
        "IMPORT_QUARANTINE_RETENTION_DAYS",
    ):
        assert variable in compose
        assert f"${{{variable}:?" in production


def _json_document(script: str, name: str) -> str:
    match = re.search(
        rf"cat > /tmp/{re.escape(name)} <<EOF\n(?P<body>.*?)\nEOF",
        script,
        flags=re.DOTALL,
    )
    assert match is not None
    return match.group("body")
