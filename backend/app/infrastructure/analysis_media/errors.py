from __future__ import annotations


class MediaPreprocessingError(RuntimeError):
    """Stable local-media preprocessing failure without path or process leakage."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
