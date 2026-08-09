from enum import StrEnum


class AuthErrorCode(StrEnum):
    EMAIL_ALREADY_REGISTERED = "email_already_registered"
    INVALID_CREDENTIALS = "invalid_credentials"
    UNAUTHENTICATED = "unauthenticated"


class AuthError(Exception):
    def __init__(self, code: AuthErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class DuplicateEmailError(RuntimeError):
    """Raised by an authentication repository on a unique email conflict."""
