from __future__ import annotations

from enum import StrEnum


class StorageFileErrorCode(StrEnum):
    NOT_FOUND = "not_found"
    IN_USE = "storage_file_in_use"
    STORAGE_UNAVAILABLE = "storage_unavailable"


class StorageFileError(RuntimeError):
    def __init__(self, code: StorageFileErrorCode) -> None:
        self.code = code
        super().__init__(code.value)
