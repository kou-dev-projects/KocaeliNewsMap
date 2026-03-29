from __future__ import annotations
from .cache import RedisGeoCache
from .config import GeocodingConfig, load_geocoding_config
from .metrics import get_metrics
from .providers.mock import MockGeocodingProvider
from .providers.nominatim import NominatimProvider
from .providers.opencage import OpenCageProvider
from .queue import GeocodingQueue
from .service import GeocodingService


def build_geocoding_service(
    config: GeocodingConfig | None = None,
) -> GeocodingService:
    cfg = config or load_geocoding_config()

    match cfg.provider:
        case "mock":
            provider = MockGeocodingProvider()
        case "nominatim":
            provider = NominatimProvider(cfg)
        case "opencage":
            provider = OpenCageProvider(cfg)
        case _:
            raise ValueError(f"Bilinmeyen geocoding provider: {cfg.provider!r}")

    return GeocodingService(
        provider=provider,
        cache=RedisGeoCache(cfg.redis_url, cfg.cache_ttl_seconds),
        queue=GeocodingQueue(),
        metrics=get_metrics(),
        config=cfg,
    )