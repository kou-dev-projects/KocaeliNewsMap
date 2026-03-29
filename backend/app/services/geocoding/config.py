from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from app.settings import settings


@dataclass(frozen=True)
class GeocodingConfig:
    provider: str
    nominatim_url: str
    user_agent: str
    timeout: int
    cache_ttl_seconds: int
    redis_url: str
    max_retries: int
    min_confidence: float
    opencage_api_key: Optional[str]    # None → OpenCage provider devre dışı


def load_geocoding_config() -> GeocodingConfig:
    return GeocodingConfig(
        provider=settings.geocoding_provider,
        nominatim_url=settings.nominatim_url,
        user_agent=settings.nominatim_user_agent,
        timeout=settings.geocoding_timeout,
        cache_ttl_seconds=settings.geocoding_cache_ttl,
        redis_url=settings.redis_url,
        max_retries=settings.geocoding_max_retries,
        min_confidence=settings.geocoding_min_confidence,
        opencage_api_key=settings.opencage_api_key,
    )