"""Administrator-managed execution routes for video AI analysis."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.application.auth import CurrentUser

from .ai_provider_models import (
    AiProviderAuthMode as AiProviderAuthMode,
)
from .ai_provider_models import (
    AiProviderEngine as AiProviderEngine,
)
from .ai_provider_models import (
    AiProviderError as AiProviderError,
)
from .ai_provider_models import (
    AiProviderErrorCode as AiProviderErrorCode,
)
from .ai_provider_models import (
    AiProviderProfile as AiProviderProfile,
)
from .ai_provider_models import (
    AiProviderRepository as AiProviderRepository,
)
from .ai_provider_models import (
    AiProviderSecretCipher as AiProviderSecretCipher,
)
from .ai_provider_models import (
    AnalysisAgentAvailability,
)
from .ai_provider_models import (
    DuplicateAiProviderKeyError as DuplicateAiProviderKeyError,
)
from .ai_provider_validation import (
    require_admin as _require_admin,
)
from .ai_provider_validation import (
    validated_base_url as _validated_base_url,
)
from .ai_provider_validation import (
    validated_key as _validated_key,
)
from .ai_provider_validation import (
    validated_model as _validated_model,
)
from .ai_provider_validation import (
    validated_name as _validated_name,
)
from .ai_provider_validation import (
    validated_profile as _validated_profile,
)


class AiProviderService:
    def __init__(
        self,
        repository: AiProviderRepository,
        cipher: AiProviderSecretCipher,
        *,
        now: Callable[[], datetime],
        availability: AnalysisAgentAvailability | None = None,
    ) -> None:
        self._repository = repository
        self._cipher = cipher
        self._now = now
        self._availability = availability

    async def list_profiles(self, actor: CurrentUser) -> tuple[AiProviderProfile, ...]:
        _require_admin(actor)
        return await self._repository.list_profiles()

    async def agent_available(self, actor: CurrentUser) -> bool:
        _require_admin(actor)
        return (
            await self._availability.is_available(self._now())
            if self._availability is not None
            else False
        )

    async def create_profile(
        self,
        actor: CurrentUser,
        *,
        key: str,
        display_name: str,
        engine: AiProviderEngine,
        auth_mode: AiProviderAuthMode,
        base_url: str | None,
        model: str,
        api_key: str | None,
    ) -> AiProviderProfile:
        _require_admin(actor)
        normalized = _validated_profile(
            key=key,
            display_name=display_name,
            engine=engine,
            auth_mode=auth_mode,
            base_url=base_url,
            model=model,
            api_key=api_key,
            require_api_key=True,
        )
        encrypted = self._encrypted(normalized[0], auth_mode, api_key)
        try:
            return await self._repository.create_profile(
                key=normalized[0],
                display_name=normalized[1],
                engine=engine,
                auth_mode=auth_mode,
                base_url=normalized[2],
                model=normalized[3],
                credential_ciphertext=encrypted,
                credential_key_id=self._cipher.key_id if encrypted else None,
                now=self._now(),
            )
        except DuplicateAiProviderKeyError as exc:
            raise AiProviderError(AiProviderErrorCode.CONFLICT) from exc

    async def update_profile(
        self,
        actor: CurrentUser,
        key: str,
        *,
        display_name: str | None,
        engine: AiProviderEngine | None,
        auth_mode: AiProviderAuthMode | None,
        base_url: str | None,
        base_url_changed: bool,
        model: str | None,
        api_key: str | None,
    ) -> AiProviderProfile:
        _require_admin(actor)
        normalized_key = _validated_key(key)
        current = await self._repository.get_profile(normalized_key)
        if current is None:
            raise AiProviderError(AiProviderErrorCode.NOT_FOUND)
        effective_engine = engine or current.engine
        effective_auth = auth_mode or current.auth_mode
        effective_base_url = (
            None
            if effective_auth is AiProviderAuthMode.HOST_LOGIN
            else (base_url if base_url_changed else current.base_url)
        )
        effective_name = display_name or current.display_name
        effective_model = model or current.model
        _validated_profile(
            key=normalized_key,
            display_name=effective_name,
            engine=effective_engine,
            auth_mode=effective_auth,
            base_url=effective_base_url,
            model=effective_model,
            api_key=api_key
            if api_key is not None
            else ("configured" if current.credential_configured else None),
            require_api_key=True,
        )
        encrypted = self._encrypted(normalized_key, effective_auth, api_key)
        profile = await self._repository.update_profile(
            normalized_key,
            display_name=(
                _validated_name(display_name) if display_name is not None else None
            ),
            engine=engine,
            auth_mode=auth_mode,
            base_url=(
                _validated_base_url(effective_base_url, effective_auth)
                if base_url_changed
                or (
                    effective_auth is AiProviderAuthMode.HOST_LOGIN
                    and current.base_url is not None
                )
                else None
            ),
            base_url_changed=base_url_changed
            or (
                effective_auth is AiProviderAuthMode.HOST_LOGIN
                and current.base_url is not None
            ),
            model=_validated_model(model) if model is not None else None,
            credential_ciphertext=encrypted,
            credential_key_id=self._cipher.key_id if encrypted else None,
            credential_changed=(
                api_key is not None or effective_auth is AiProviderAuthMode.HOST_LOGIN
            ),
            now=self._now(),
        )
        if profile is None:
            raise AiProviderError(AiProviderErrorCode.NOT_FOUND)
        return profile

    async def activate_profile(self, actor: CurrentUser, key: str) -> AiProviderProfile:
        _require_admin(actor)
        normalized_key = _validated_key(key)
        current = await self._repository.get_profile(normalized_key)
        if current is None:
            raise AiProviderError(AiProviderErrorCode.NOT_FOUND)
        if (
            current.auth_mode is AiProviderAuthMode.API_KEY
            and not current.credential_configured
        ):
            raise AiProviderError(AiProviderErrorCode.INVALID_PROFILE)
        profile = await self._repository.activate_profile(
            normalized_key, now=self._now()
        )
        if profile is None:
            raise AiProviderError(AiProviderErrorCode.NOT_FOUND)
        return profile

    async def delete_profile(self, actor: CurrentUser, key: str) -> None:
        _require_admin(actor)
        normalized_key = _validated_key(key)
        current = await self._repository.get_profile(normalized_key)
        if current is None:
            raise AiProviderError(AiProviderErrorCode.NOT_FOUND)
        if current.is_active:
            raise AiProviderError(AiProviderErrorCode.ACTIVE_DELETE)
        if not await self._repository.delete_profile(normalized_key):
            raise AiProviderError(AiProviderErrorCode.NOT_FOUND)

    def _encrypted(
        self,
        provider_key: str,
        auth_mode: AiProviderAuthMode,
        api_key: str | None,
    ) -> bytes | None:
        if auth_mode is AiProviderAuthMode.HOST_LOGIN or api_key is None:
            return None
        return self._cipher.encrypt(provider_key, api_key.strip())
