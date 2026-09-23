from dataclasses import replace
from hashlib import sha256

from app.services.provider_types import ProviderAccessContextRef


def test_legacy_context_keeps_its_persisted_shape_and_generation() -> None:
    document = {
        "provider_key": "generic",
        "profile_version": "default",
        "access_mode": "anonymous",
        "credential_version_id": None,
        "egress_affinity_id": "default",
        "client_profile_id": "yt-dlp-default",
        "attestation_provider_version": None,
        "engine_commit": "pinned",
    }
    context = ProviderAccessContextRef.from_document(document)
    old_identity = "\x1f".join(
        (
            "generic",
            "default",
            "anonymous",
            "",
            "default",
            "yt-dlp-default",
            "",
            "pinned",
        )
    )

    assert context.runtime_revision == "legacy"
    assert context.to_document() == document
    assert context.generation_id == sha256(old_identity.encode()).hexdigest()

    current = replace(context, runtime_revision="a" * 64)
    assert current.to_document()["runtime_revision"] == "a" * 64
    assert current.generation_id != context.generation_id
