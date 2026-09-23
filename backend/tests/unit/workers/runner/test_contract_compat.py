from app.workers.runner.contracts import ProviderAccessContextContract


def test_internal_context_accepts_old_and_new_release_shapes() -> None:
    old = {
        "provider_key": "generic",
        "profile_version": "default",
        "access_mode": "anonymous",
        "credential_version_id": None,
        "egress_affinity_id": "default",
        "client_profile_id": "yt-dlp-default",
        "attestation_provider_version": None,
        "engine_commit": "pinned",
    }
    legacy = ProviderAccessContextContract.model_validate(old)
    assert legacy.to_domain().runtime_revision == "legacy"
    assert ProviderAccessContextContract.from_domain(legacy.to_domain()).model_dump(
        exclude_none=True
    ) == {key: value for key, value in old.items() if value is not None}

    current = ProviderAccessContextContract.model_validate(
        {**old, "runtime_revision": "a" * 64}
    )
    assert current.to_domain().runtime_revision == "a" * 64
    assert (
        ProviderAccessContextContract.from_domain(current.to_domain()).runtime_revision
        == "a" * 64
    )
