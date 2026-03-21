from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


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
        provider=os.getenv("GEOCODING_PROVIDER", "mock"),
        nominatim_url=os.getenv(
            "NOMINATIM_URL", "https://nominatim.openstreetmap.org"
        ),
        user_agent=os.getenv(
            "NOMINATIM_USER_AGENT", "PULSE/1.0 kocaeli-news-platform"
        ),
        timeout=int(os.getenv("GEOCODING_TIMEOUT", "10")),
        cache_ttl_seconds=int(os.getenv("GEOCODING_CACHE_TTL", "86400")),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        max_retries=int(os.getenv("GEOCODING_MAX_RETRIES", "2")),
        min_confidence=float(os.getenv("GEOCODING_MIN_CONFIDENCE", "0.3")),
        opencage_api_key=os.getenv("OPENCAGE_API_KEY"),
    )