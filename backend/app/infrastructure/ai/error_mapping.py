from __future__ import annotations

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

from app.infrastructure.ai.errors import (
    AIProviderError,
    ProviderInvalidResponse,
    ProviderRateLimited,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)


def provider_error(error: Exception) -> AIProviderError:
    if isinstance(error, RateLimitError):
        return ProviderRateLimited()
    if isinstance(error, (APITimeoutError, TimeoutError)):
        return ProviderTimeout()
    if isinstance(error, APIConnectionError):
        return ProviderUnavailable()
    if isinstance(error, APIStatusError):
        if error.status_code == 429:
            return ProviderRateLimited()
        if error.status_code >= 500:
            return ProviderUnavailable()
        return ProviderRejected()
    return ProviderInvalidResponse()
