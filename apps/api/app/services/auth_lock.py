from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
import hashlib
from time import monotonic

from app.core.errors import AppError


class AuthLockScope(StrEnum):
    LOGIN_EMAIL = "login_email"
    LOGIN_IP = "login_ip"
    REGISTER_IP = "register_ip"


@dataclass
class LockCounter:
    count: int = 0
    expires_at: float = 0


class InMemoryAuthLock:
    def __init__(self, max_failures: int = 5, lock_seconds: int = 900, register_limit: int = 10) -> None:
        self.max_failures = max_failures
        self.lock_seconds = lock_seconds
        self.register_limit = register_limit
        self._counters: dict[str, LockCounter] = defaultdict(LockCounter)

    def assert_login_allowed(self, email: str, ip: str) -> None:
        if self.is_login_locked(email, ip):
            raise AppError("auth_locked", "登录失败次数过多，请稍后再试", 429)

    def record_login_failure(self, email: str, ip: str) -> None:
        for key in (self._key(AuthLockScope.LOGIN_EMAIL, _email_hash(email)), self._key(AuthLockScope.LOGIN_IP, ip)):
            counter = self._active_counter(key)
            counter.count += 1
            counter.expires_at = monotonic() + self.lock_seconds

    def clear_login(self, email: str) -> None:
        self._counters.pop(self._key(AuthLockScope.LOGIN_EMAIL, _email_hash(email)), None)

    def is_login_locked(self, email: str, ip: str) -> bool:
        return any(
            self._active_counter(key).count >= self.max_failures
            for key in (self._key(AuthLockScope.LOGIN_EMAIL, _email_hash(email)), self._key(AuthLockScope.LOGIN_IP, ip))
        )

    def assert_register_allowed(self, ip: str) -> None:
        key = self._key(AuthLockScope.REGISTER_IP, ip)
        counter = self._active_counter(key)
        if counter.count >= self.register_limit:
            raise AppError("auth_locked", "注册请求过于频繁，请稍后再试", 429)
        counter.count += 1
        counter.expires_at = monotonic() + 3600

    def _active_counter(self, key: str) -> LockCounter:
        counter = self._counters[key]
        if counter.expires_at and counter.expires_at <= monotonic():
            counter.count = 0
            counter.expires_at = 0
        return counter

    @staticmethod
    def _key(scope: AuthLockScope, identity: str) -> str:
        return f"video:auth-lock:{scope.value}:{identity}"


class RedisAuthLock:
    def __init__(self, redis_client, max_failures: int = 5, lock_seconds: int = 900, register_limit: int = 10) -> None:
        self.redis = redis_client
        self.max_failures = max_failures
        self.lock_seconds = lock_seconds
        self.register_limit = register_limit

    def assert_login_allowed(self, email: str, ip: str) -> None:
        if self.is_login_locked(email, ip):
            raise AppError("auth_locked", "登录失败次数过多，请稍后再试", 429)

    def record_login_failure(self, email: str, ip: str) -> None:
        for key in (self._key(AuthLockScope.LOGIN_EMAIL, _email_hash(email)), self._key(AuthLockScope.LOGIN_IP, ip)):
            count = self.redis.incr(key)
            if count == 1:
                self.redis.expire(key, self.lock_seconds)

    def clear_login(self, email: str) -> None:
        self.redis.delete(self._key(AuthLockScope.LOGIN_EMAIL, _email_hash(email)))

    def is_login_locked(self, email: str, ip: str) -> bool:
        return any(
            int(self.redis.get(key) or 0) >= self.max_failures
            for key in (self._key(AuthLockScope.LOGIN_EMAIL, _email_hash(email)), self._key(AuthLockScope.LOGIN_IP, ip))
        )

    def assert_register_allowed(self, ip: str) -> None:
        key = self._key(AuthLockScope.REGISTER_IP, ip)
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, 3600)
        if count > self.register_limit:
            raise AppError("auth_locked", "注册请求过于频繁，请稍后再试", 429)

    @staticmethod
    def _key(scope: AuthLockScope, identity: str) -> str:
        return f"video:auth-lock:{scope.value}:{identity}"


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()
