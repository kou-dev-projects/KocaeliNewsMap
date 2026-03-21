from __future__ import annotations

import logging

from .cache import RedisGeoCache
from .config import GeocodingConfig
from .exceptions import ProviderRateLimitError, ProviderUnavailableError
from .metrics import GeocodingMetrics
from .providers.base import GeocodingProvider
from .queue import GeocodingQueue
from .schemas import (
    GeocodingFailure,
    GeocodingInput,
    GeocodingResult,
    _normalize_for_compare,
)

logger = logging.getLogger(__name__)

_LAT_MIN, _LAT_MAX = 40.35, 41.15
_LNG_MIN, _LNG_MAX = 29.10, 30.90

KOCAELI_DISTRICTS = frozenset(
    _normalize_for_compare(name)
    for name in (
        "İzmit",
        "Gebze",
        "Darıca",
        "Gölcük",
        "Körfez",
        "Kartepe",
        "Başiskele",
        "Çayırova",
        "Dilovası",
        "Kandıra",
        "Karamürsel",
        "Derince",
    )
)


class GeocodingService:
    def __init__(
        self,
        provider: GeocodingProvider,
        cache: RedisGeoCache,
        queue: GeocodingQueue,
        metrics: GeocodingMetrics,
        config: GeocodingConfig,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._queue = queue
        self._metrics = metrics
        self._cfg = config

    def geocode(
        self, input_data: GeocodingInput
    ) -> GeocodingResult | GeocodingFailure:
        cached = self._cache.get(input_data)
        if cached:
            self._metrics.record_success(
                source="cache",
                district=cached.district,
                confidence=cached.confidence,
            )
            return cached

        try:
            result = self._provider.geocode(input_data)
        except ProviderRateLimitError as exc:
            self._metrics.record_rate_limit(
                exc.provider,
                exc.retry_after,
                address=input_data.address,
            )
            queued = self._queue.enqueue(
                input_data,
                reason=f"rate_limit:{exc.provider}",
            )
            return GeocodingFailure(
                address=input_data.address,
                reason=(
                    f"Rate limit — kuyruğa alındı ({exc.retry_after}s)"
                    if queued
                    else "Rate limit — kuyruk dolu, adres düşürüldü"
                ),
                failure_type="rate_limit" if queued else "queue_full",
                news_id=input_data.news_id,
            )
        except ProviderUnavailableError as exc:
            self._metrics.record_failure(
                input_data.address,
                "provider_unavailable",
                str(exc),
            )
            return GeocodingFailure(
                address=input_data.address,
                reason=f"Provider yanıtsız: {type(exc).__name__}",
                failure_type="provider_error",
                news_id=input_data.news_id,
            )
        except Exception as exc:
            self._metrics.record_failure(
                input_data.address,
                "unexpected_error",
                type(exc).__name__,
            )
            logger.exception(
                "geocoding.unexpected_error",
                extra={"address": input_data.address[:60]},
            )
            return GeocodingFailure(
                address=input_data.address,
                reason=f"Beklenmedik hata: {type(exc).__name__}",
                failure_type="provider_error",
                news_id=input_data.news_id,
            )

        if result is None:
            self._metrics.record_failure(
                input_data.address,
                "not_found",
                "Provider sonuç döndürmedi",
            )
            return GeocodingFailure(
                address=input_data.address,
                reason="Adres bulunamadı",
                failure_type="not_found",
                news_id=input_data.news_id,
            )

        if result.confidence < self._cfg.min_confidence:
            self._metrics.record_failure(
                input_data.address,
                "low_confidence",
                f"confidence={result.confidence:.3f}",
            )
            return GeocodingFailure(
                address=input_data.address,
                reason=f"Düşük güven skoru: {result.confidence:.3f}",
                failure_type="low_confidence",
                news_id=input_data.news_id,
            )

        if not self._is_kocaeli(result):
            self._metrics.record_failure(
                input_data.address,
                "out_of_bounds",
                f"({result.lat:.4f}, {result.lng:.4f})",
            )
            return GeocodingFailure(
                address=input_data.address,
                reason=f"Kocaeli dışı koordinat: {result.display_name[:60]}",
                failure_type="out_of_bounds",
                news_id=input_data.news_id,
            )

        self._cache.set(input_data, result)
        self._metrics.record_success(
            source=result.source,
            district=result.district,
            confidence=result.confidence,
        )
        return result

    def metrics_summary(self) -> dict:
        return {
            **self._metrics.summary(),
            "cache_available": self._cache.available,
            "queue_size": self._queue.size,
            "provider": self._provider.name,
        }

    def _is_kocaeli(self, result: GeocodingResult) -> bool:
        display = _normalize_for_compare(result.display_name)
        if "kocaeli" in display or "izmit" in display:
            return True
        if (
            result.district
            and _normalize_for_compare(result.district) in KOCAELI_DISTRICTS
        ):
            return True
        if _LAT_MIN <= result.lat <= _LAT_MAX and _LNG_MIN <= result.lng <= _LNG_MAX:
            return True
        return False
