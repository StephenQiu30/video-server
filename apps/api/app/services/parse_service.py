from __future__ import annotations

from app.core.errors import AppError
from app.schemas import ParseResponse
from app.services.platforms import find_platform_profile
from app.sources.models import SourceRequest, source_info_to_parse_response
from app.sources.registry import SourceAdapterRegistry


class ParseService:
    """Unified video parse service that delegates to the adapter registry."""

    def __init__(self, registry: SourceAdapterRegistry | None = None) -> None:
        self._registry = registry or SourceAdapterRegistry()

    def parse(self, url: str, format_id: str | None = None) -> ParseResponse:
        request = SourceRequest.from_url(url, format_id=format_id)
        adapter = self._registry.get_adapter(request)
        try:
            info = adapter.parse(request)
        except AppError:
            raise
        except Exception as exc:
            raise adapter.map_error(exc) from exc

        platform_profile = find_platform_profile(url)
        return source_info_to_parse_response(
            url=url,
            info=info,
            platform_profile=platform_profile,
        )
