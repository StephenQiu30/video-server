"""Pure local-installation request authorization boundary."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InstallationPrincipal:
    owner_id: str
    bearer_token: str


@dataclass(frozen=True, slots=True)
class RequestContext:
    method: str
    authority: str | None
    authorization: str | None
    origin: str | None
    fetch_site: str | None
    content_type: str | None = None


class RequestGate:
    """Authorize one BFF request without exposing the installation token."""

    def __init__(
        self,
        principal: InstallationPrincipal,
        *,
        web_origin: str,
        api_authority: str,
    ) -> None:
        raise NotImplementedError("request gate construction is not implemented")

    def authorize(self, context: RequestContext) -> str:
        """Return the immutable owner ID or raise a canonical DomainError."""

        raise NotImplementedError("request authorization is not implemented")
