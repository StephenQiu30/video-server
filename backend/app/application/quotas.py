"""Admission budgets for owned work, independent of HTTP and persistence."""

from dataclasses import dataclass


class QuotaExceeded(Exception):
    def __init__(self, code: str, *, retry_after: int = 60) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after


@dataclass(frozen=True)
class QuotaPolicy:
    max_active_per_owner: int = 5
    max_active_global: int = 200
    daily_tasks: int = 50
    daily_bytes: int = 100 * 1024**3
    storage_bytes: int = 100 * 1024**3
    daily_analysis_attempts: int = 60
    download_bytes: int = 20 * 1024**3
    document_normalized_bytes: int = 8_000_000
    report_bytes: int = 16 * 1024**2
    thumbnail_bytes: int = 2_000_000

    def __post_init__(self) -> None:
        if any(value <= 0 for value in vars(self).values()):
            raise ValueError("quota limits must be positive")
