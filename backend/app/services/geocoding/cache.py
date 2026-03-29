from __future__ import annotations
import json
import logging
from typing import Optional

from .schemas import GeocodingInput, GeocodingResult

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "pulse:geo:v1"

try:
    import redis as redis_lib
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False


class RedisGeoCache:

    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._client: Optional["redis_lib.Redis"] = None
        self._available = False

        if not _REDIS_AVAILABLE:
            logger.warning(
                "geocoding.cache.unavailable",
                extra={"reason": "redis-py kurulu değil", "impact": "her adres API'ye gider"},
            )
            return

        try:
            self._client = redis_lib.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,    # bağlantı timeout — servis başlangıcını bloke etmez
                socket_timeout=1,            # komut timeout
            )
            self._client.ping()
            self._available = True
            logger.info(
                "geocoding.cache.ready",
                extra={"ttl_hours": ttl_seconds // 3600, "redis_url": redis_url.split("@")[-1]},
            )
        except Exception as exc:
            logger.warning(
                "geocoding.cache.unavailable",
                extra={
                    "reason": type(exc).__name__,
                    "impact": "cache bypass — her adres API'ye gider",
                },
            )

    @property
    def available(self) -> bool:
        return self._available

    def get(self, input_data: GeocodingInput) -> Optional[GeocodingResult]:
        if not self._client:
            return None
        key = self._key(input_data)
        try:
            raw = self._client.get(key)
            if raw:
                data = json.loads(raw)
                return GeocodingResult(**{**data, "source": "cache"})
        except Exception as exc:
            # Cache hatası asla ana akışı durdurmamalı
            logger.warning(
                "geocoding.cache.get_error",
                extra={"key": key, "error": type(exc).__name__},
            )
        return None

    def set(self, input_data: GeocodingInput, result: GeocodingResult) -> None:
        if not self._client:
            return
        key = self._key(input_data)
        try:
            payload = json.dumps(
                {
                    "address": result.address,
                    "lat": result.lat,
                    "lng": result.lng,
                    "display_name": result.display_name,
                    "confidence": result.confidence,
                    "source": result.source,
                    "provider_version": result.provider_version,
                    "district": result.district,
                    "geocoded_at": result.geocoded_at,
                },
                ensure_ascii=False,
            )
            self._client.setex(key, self._ttl, payload)
        except Exception as exc:
            logger.warning(
                "geocoding.cache.set_error",
                extra={"key": key, "error": type(exc).__name__},
            )

    def invalidate_provider(self, provider_prefix: str) -> int:
       
        if not self._client:
            return 0
        count = 0
        try:
            for key in self._client.scan_iter(f"{_CACHE_KEY_PREFIX}:*"):
                try:
                    raw = self._client.get(key)
                    if raw:
                        data = json.loads(raw)
                        if data.get("provider_version", "").startswith(provider_prefix):
                            self._client.delete(key)
                            count += 1
                except Exception:
                    continue
        except Exception as exc:
            logger.error(
                "geocoding.cache.invalidation_error",
                extra={"error": type(exc).__name__},
            )
        logger.info(
            "geocoding.cache.invalidated",
            extra={"count": count, "provider_prefix": provider_prefix},
        )
        return count

    def _key(self, input_data: GeocodingInput) -> str:
        return f"{_CACHE_KEY_PREFIX}:{input_data.normalized()}"