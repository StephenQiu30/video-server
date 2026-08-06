from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID

from app.application.downloads.errors import (
    ApplicationError,
    ApplicationErrorCode,
    MediaInspectionFailure,
    MediaInspectionTimeout,
    PersistenceIdempotencyConflict,
)
from app.application.downloads.inspection_models import (
    FormatCreate,
    InspectionCreate,
    InspectionView,
    RunnerFormat,
)
from app.application.downloads.plans import plan_fingerprint, plan_to_documents
from app.application.downloads.ports import (
    DownloadRepository,
    MediaRunner,
    RequestFingerprinter,
    UrlCipher,
    UrlValidator,
)
from app.application.downloads.validation import (
    validate_idempotency_key,
    validate_now,
    validate_owner_hash,
)
from app.application.downloads.views import inspection_view


class InspectMedia:
    def __init__(
        self,
        *,
        repository: DownloadRepository,
        runner: MediaRunner,
        url_validator: UrlValidator,
        url_cipher: UrlCipher,
        fingerprinter: RequestFingerprinter,
        now: Callable[[], datetime],
        new_id: Callable[[], UUID],
        inspection_ttl: timedelta,
        max_duration_seconds: int,
    ) -> None:
        if inspection_ttl <= timedelta(0) or max_duration_seconds <= 0:
            raise ValueError("inspection limits must be positive")
        self._repository = repository
        self._runner = runner
        self._url_validator = url_validator
        self._url_cipher = url_cipher
        self._fingerprinter = fingerprinter
        self._now = now
        self._new_id = new_id
        self._ttl = inspection_ttl
        self._max_duration = max_duration_seconds

    async def __call__(
        self, url: str, owner_hash: str, idempotency_key: str
    ) -> InspectionView:
        owner_hash = validate_owner_hash(owner_hash)
        idempotency_key = validate_idempotency_key(idempotency_key)
        try:
            validated_url = self._url_validator.validate(url)
        except ValueError as exc:
            raise ApplicationError(ApplicationErrorCode.INVALID_URL) from exc
        try:
            result = await self._runner.inspect(validated_url)
        except MediaInspectionTimeout as exc:
            raise ApplicationError(ApplicationErrorCode.INSPECTION_TIMEOUT) from exc
        except MediaInspectionFailure as exc:
            raise ApplicationError(ApplicationErrorCode.INSPECTION_FAILED) from exc
        if result.duration_seconds <= 0:
            raise ApplicationError(ApplicationErrorCode.INSPECTION_FAILED)
        if result.duration_seconds > self._max_duration:
            raise ApplicationError(ApplicationErrorCode.DURATION_LIMIT_EXCEEDED)

        now = validate_now(self._now())
        expires_at = now + self._ttl
        formats = self._formats(result.formats, expires_at)
        if not formats:
            raise ApplicationError(ApplicationErrorCode.FORMAT_UNAVAILABLE)
        envelope = self._url_cipher.encrypt(validated_url)
        command = InspectionCreate(
            id=self._new_id(),
            owner_hash=owner_hash,
            idempotency_key=idempotency_key,
            request_fingerprint=self._fingerprinter.fingerprint(
                "inspection", validated_url
            ),
            url_ciphertext=envelope.ciphertext,
            url_nonce=envelope.nonce,
            url_key_id=envelope.key_id,
            extractor_key=_required(result.extractor_key),
            provider_media_id=_required(result.provider_media_id),
            title=_required(result.title),
            duration_seconds=result.duration_seconds,
            metadata={},
            expires_at=expires_at,
            formats=formats,
        )
        try:
            saved = await self._repository.save_inspection(command)
        except PersistenceIdempotencyConflict as exc:
            raise ApplicationError(ApplicationErrorCode.IDEMPOTENCY_CONFLICT) from exc
        return inspection_view(saved.inspection)

    def _formats(
        self, formats: tuple[RunnerFormat, ...], expires_at: datetime
    ) -> tuple[FormatCreate, ...]:
        unique: dict[str, FormatCreate] = {}
        for item in formats:
            semantic, hints = plan_to_documents(item.plan)
            fingerprint = plan_fingerprint(semantic)
            unique.setdefault(
                fingerprint,
                FormatCreate(
                    id=self._new_id(),
                    display_name=_required(item.display_name),
                    plan_fingerprint=fingerprint,
                    semantic_plan=semantic,
                    provider_hints=hints,
                    expires_at=expires_at,
                ),
            )
        return tuple(unique.values())


def _required(value: str) -> str:
    value = value.strip()
    if not value:
        raise ApplicationError(ApplicationErrorCode.INSPECTION_FAILED)
    return value
