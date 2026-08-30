from enum import StrEnum


class AuthErrorCode(StrEnum):
    ADMIN_BOOTSTRAP_REQUIRED = "admin_bootstrap_required"
    EMAIL_ALREADY_REGISTERED = "email_already_registered"
    USERNAME_ALREADY_REGISTERED = "username_already_registered"
    INVALID_CREDENTIALS = "invalid_credentials"
    INVALID_USERNAME = "invalid_username"
    FORBIDDEN = "forbidden"
    USER_NOT_FOUND = "user_not_found"
    SELF_ADMIN_CHANGE = "self_admin_change"
    UNAUTHENTICATED = "unauthenticated"


class AuthError(Exception):
    def __init__(self, code: AuthErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class DuplicateEmailError(RuntimeError):
    """Raised by an authentication repository on a unique email conflict."""


class DuplicateUsernameError(RuntimeError):
    """Raised when a normalized username is already assigned."""
