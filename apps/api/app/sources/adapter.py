from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.errors import AppError, ErrorCode
from app.sources.models import SourceInfo, SourceRequest


class VideoSourceAdapter(ABC):
    """Abstract protocol for video source adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique adapter name."""

    @abstractmethod
    def supports(self, request: SourceRequest) -> bool:
        """Return True if this adapter can handle the given request."""

    @abstractmethod
    def parse(self, request: SourceRequest) -> SourceInfo:
        """Parse the video source and return SourceInfo."""

    @abstractmethod
    def map_error(self, exc: Exception) -> AppError:
        """Map an adapter exception to a unified AppError."""
