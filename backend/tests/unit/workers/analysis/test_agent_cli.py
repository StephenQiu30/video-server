from __future__ import annotations

from dataclasses import dataclass

import pytest
from app.workers.analysis.agent_cli import ANALYSIS_STORAGE_PROBE, _verify_storage


@dataclass(frozen=True, slots=True)
class _Stat:
    size_bytes: int


class _Storage:
    def __init__(self, *, missing: bool = False, fails: bool = False):
        self.result = None if missing else _Stat(1)
        self.fails = fails
        self.requested: str | None = None

    async def stat(self, object_key: str) -> _Stat | None:
        self.requested = object_key
        if self.fails:
            raise RuntimeError("access denied")
        return self.result


@pytest.mark.asyncio
async def test_storage_probe_is_readable() -> None:
    storage = _Storage()

    await _verify_storage(storage)

    assert storage.requested == ANALYSIS_STORAGE_PROBE


@pytest.mark.asyncio
@pytest.mark.parametrize("storage", [_Storage(missing=True), _Storage(fails=True)])
async def test_storage_probe_reports_unavailable_without_leaking_details(
    storage: _Storage,
) -> None:
    with pytest.raises(SystemExit, match="not ready: analysis MinIO") as error:
        await _verify_storage(storage)

    assert "access denied" not in str(error.value)
