"""Built-in provider catalog assembled from cohesive policy groups."""

from app.runner.provider_catalog_core import CORE_PROVIDER_PROFILES
from app.runner.provider_catalog_public import PUBLIC_PROVIDER_PROFILES
from app.runner.provider_catalog_social import SOCIAL_PROVIDER_PROFILES
from app.runner.provider_registry import ProviderProfile

DEFAULT_PROVIDER_PROFILES: tuple[ProviderProfile, ...] = (
    *CORE_PROVIDER_PROFILES,
    *SOCIAL_PROVIDER_PROFILES,
    *PUBLIC_PROVIDER_PROFILES,
)
