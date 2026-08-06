from __future__ import annotations

import httpx
from ollama import ResponseError
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
    if isinstance(error, AIProviderError):
        return error
    if isinstance(error, RateLimitError):
        return ProviderRateLimited()
    if isinstance(error, (APITimeoutError, httpx.TimeoutException, TimeoutError)):
        return ProviderTimeout()
    if isinstance(error, (APIConnectionError, httpx.RequestError)):
        return ProviderUnavailable()
    if isinstance(error, ResponseError):
        return _status_error(error.status_code)
    if isinstance(error, APIStatusError):
        return _status_error(error.status_code)
    return ProviderInvalidResponse()


def _status_error(status_code: int) -> AIProviderError:
    if status_code == 429:
        return ProviderRateLimited()
    if status_code >= 500 or status_code < 0:
        return ProviderUnavailable()
    return ProviderRejected()
