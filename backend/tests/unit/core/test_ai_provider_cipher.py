import pytest
from app.core.ai_provider_cipher import FernetAiProviderSecretCipher
from app.core.url_cipher import URLCipher
from cryptography.fernet import Fernet


def test_ai_provider_secret_is_bound_to_profile_and_key_version() -> None:
    cipher = FernetAiProviderSecretCipher(
        URLCipher(Fernet.generate_key()), key_id="fernet-test"
    )
    encrypted = cipher.encrypt("primary", "secret-value")

    assert cipher.decrypt("primary", encrypted, "fernet-test") == "secret-value"
    with pytest.raises(ValueError):
        cipher.decrypt("secondary", encrypted, "fernet-test")
    with pytest.raises(ValueError):
        cipher.decrypt("primary", encrypted, "unknown")
