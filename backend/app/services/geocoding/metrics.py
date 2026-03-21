from __future__ import annotations

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GeocodingMetrics:
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    total_requests: int = 0
    total_success: int = 0
    total_failure: int = 0
    cache_hits: int = 0
    provider_calls: int = 0

    failure_by_type: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    success_by_district: dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    failed_addresses: list[str] = field(default_factory=list)
    _max_failed_addresses: int = 100

    def record_success(
        self,
        source: str,
        district: Optional[str],
        confidence: float,
    ) -> None:
        with self._lock:
            self.total_requests += 1
            self.total_success += 1
            if source == "cache":
                self.cache_hits += 1
            else:
                self.provider_calls += 1
            if district:
                self.success_by_district[district] += 1

        logger.info(
            "geocoding.success",
            extra={
                "source": source,
                "district": district,
                "confidence": round(confidence, 3),
                "cache_hit_rate": self._cache_hit_rate(),
            },
        )

    def record_failure(self, address: str, failure_type: str, reason: str) -> None:
        with self._lock:
            self.total_requests += 1
            self.total_failure += 1
            self.failure_by_type[failure_type] += 1
            if len(self.failed_addresses) < self._max_failed_addresses:
                self.failed_addresses.append(address)

        logger.warning(
            "geocoding.failure",
            extra={
                "address": address[:80],
                "failure_type": failure_type,
                "reason": reason[:120],
                "total_failure_rate": self._failure_rate(),
            },
        )

    def record_rate_limit(
        self,
        provider: str,
        retry_after: float,
        address: Optional[str] = None,
    ) -> None:
        with self._lock:
            self.total_requests += 1
            self.total_failure += 1
            self.failure_by_type["rate_limit"] += 1
            if address and len(self.failed_addresses) < self._max_failed_addresses:
                self.failed_addresses.append(address)

        logger.warning(
            "geocoding.rate_limit",
            extra={
                "provider": provider,
                "retry_after_seconds": retry_after,
            },
        )

    def summary(self) -> dict:
        with self._lock:
            return {
                "total_requests": self.total_requests,
                "success_rate": self._success_rate(),
                "cache_hit_rate": self._cache_hit_rate(),
                "failure_by_type": dict(self.failure_by_type),
                "top_failure_types": self._top_failures(),
            }

    def _success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(self.total_success / self.total_requests, 3)

    def _failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(self.total_failure / self.total_requests, 3)

    def _cache_hit_rate(self) -> float:
        total_hits = self.provider_calls + self.cache_hits
        if total_hits == 0:
            return 0.0
        return round(self.cache_hits / total_hits, 3)

    def _top_failures(self) -> dict:
        return dict(
            sorted(
                self.failure_by_type.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:5]
        )


_metrics = GeocodingMetrics()


def get_metrics() -> GeocodingMetrics:
    return _metrics
