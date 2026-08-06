from __future__ import annotations

from enum import StrEnum


class AIProviderErrorCode(StrEnum):
    RATE_LIMITED = "provider_rate_limited"
    UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "provider_timeout"
    REJECTED = "provider_rejected"
    REFUSED = "provider_refused"
    INVALID_RESPONSE = "provider_invalid_response"


class AIProviderError(RuntimeError):
    code: AIProviderErrorCode

    def __init__(self, code: AIProviderErrorCode) -> None:
        self.code = code
        super().__init__(code.value)

    @property
    def retryable(self) -> bool:
        return self.code in {
            AIProviderErrorCode.RATE_LIMITED,
            AIProviderErrorCode.UNAVAILABLE,
            AIProviderErrorCode.TIMEOUT,
        }


class ProviderRateLimited(AIProviderError):
    def __init__(self) -> None:
        super().__init__(AIProviderErrorCode.RATE_LIMITED)


class ProviderUnavailable(AIProviderError):
    def __init__(self) -> None:
        super().__init__(AIProviderErrorCode.UNAVAILABLE)


class ProviderTimeout(AIProviderError):
    def __init__(self) -> None:
        super().__init__(AIProviderErrorCode.TIMEOUT)


class ProviderRejected(AIProviderError):
    def __init__(self) -> None:
        super().__init__(AIProviderErrorCode.REJECTED)


class ProviderRefused(AIProviderError):
    def __init__(self) -> None:
        super().__init__(AIProviderErrorCode.REFUSED)


class ProviderInvalidResponse(AIProviderError):
    def __init__(self) -> None:
        super().__init__(AIProviderErrorCode.INVALID_RESPONSE)
