from collections import defaultdict, deque
from time import monotonic

from app.core.errors import AppError


class InMemoryRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def assert_allowed(self, key: str) -> None:
        if self.limit <= 0:
            return
        now = monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            raise AppError("rate_limited", "请求过于频繁，请稍后再试", 429)
        hits.append(now)
