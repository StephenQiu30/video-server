"""Public policy names; no credentials, endpoint discovery or implicit fallback."""

from enum import StrEnum

from app.domain.providers import ProviderAccessMode, ProviderKey


class ProviderAccessPolicy(StrEnum):
    PUBLIC = "public"
    PUBLIC_SESSION = "public_session"
    OPERATOR_PUBLIC = "operator_public"
    PERSONAL_ENTITLED = "personal_entitled"

    @property
    def access_mode(self) -> ProviderAccessMode:
        return (
            ProviderAccessMode.ANONYMOUS
            if self is ProviderAccessPolicy.PUBLIC
            else ProviderAccessMode.OPERATOR_MANAGED
        )


def provider_access_policies(
    provider_key: str, access_modes: tuple[ProviderAccessMode, ...]
) -> tuple[ProviderAccessPolicy, ...]:
    """Only approved policies are selectable; visitor maintenance remains gated."""
    policies = []
    if ProviderAccessMode.ANONYMOUS in access_modes:
        policies.append(ProviderAccessPolicy.PUBLIC)
    if ProviderAccessMode.OPERATOR_MANAGED in access_modes:
        policies.append(
            ProviderAccessPolicy.PERSONAL_ENTITLED
            if provider_key in {ProviderKey.YOUKU, ProviderKey.QQVIDEO}
            else ProviderAccessPolicy.OPERATOR_PUBLIC
        )
    return tuple(policies)


def default_access_policy(
    provider_key: str, access_modes: tuple[ProviderAccessMode, ...]
) -> ProviderAccessPolicy:
    # Preserve the declared controlled route for challenged profiles, regardless
    # of endpoint presence. Public-only profiles keep their public default.
    # Moving a challenged profile to public by default requires canary evidence.
    policies = provider_access_policies(provider_key, access_modes)
    if not policies:
        raise ValueError("provider has no admitted access policy")
    return policies[-1]
