from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.infrastructure.jwt_tokens import JwtTokenService

NOW = datetime.now(UTC).replace(microsecond=0)
USER_ID = UUID("11111111-1111-4111-8111-111111111111")


def token_service() -> JwtTokenService:
    return JwtTokenService(
        secret=b"s" * 48,
        issuer="video-server-test",
        audience="video-web-test",
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=30),
    )


def test_jwt_pair_contains_typed_access_and_refresh_claims() -> None:
    service = token_service()

    issued = service.issue(USER_ID, NOW)
    access = service.decode_access(issued.access_token)
    refresh = service.decode_refresh(issued.refresh_token)

    assert access is not None and access.user_id == USER_ID
    assert refresh is not None and refresh.user_id == USER_ID
    assert service.decode_refresh(issued.access_token) is None
    assert service.decode_access(issued.refresh_token) is None
    assert issued.refresh_token_hash == service.digest(issued.refresh_token)


def test_jwt_rejects_tampered_and_unbounded_tokens() -> None:
    service = token_service()
    issued = service.issue(USER_ID, NOW)

    assert service.decode_access(f"{issued.access_token}x") is None
    assert service.digest("") == ""
    assert service.digest("x" * 4097) == ""
