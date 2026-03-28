from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import unicodedata


def _normalize_for_compare(value: str) -> str:
    normalized = value.strip().replace("İ", "I").replace("ı", "i").lower()
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return normalized


@dataclass(frozen=True)
class GeocodingInput:
    address: str
    district_hint: Optional[str] = None
    neighborhood: Optional[str] = None
    news_id: Optional[str] = None

    def normalized(self) -> str:
        base = _normalize_for_compare(self.address)
        hint = _normalize_for_compare(self.district_hint) if self.district_hint else None

        if hint and hint not in base:
            base = f"{base}, {hint}"
        if "kocaeli" not in base:
            base = f"{base}, kocaeli, turkey"
        return base

    def query_string(self) -> str:
        parts = []
        if self.neighborhood:
            parts.append(self.neighborhood.strip())
        parts.append(self.address.strip())

        address_norm = _normalize_for_compare(self.address)
        hint_norm = _normalize_for_compare(self.district_hint) if self.district_hint else None

        if self.district_hint and hint_norm and hint_norm not in address_norm:
            parts.append(self.district_hint.strip())
        if "kocaeli" not in address_norm:
            parts.append("Kocaeli")
        return ", ".join(parts)

@dataclass(frozen=True)
class GeocodingResult:
    address: str
    lat: float
    lng: float
    display_name: str
    confidence: float
    source: str
    provider_version: str
    district: Optional[str] = None
    geocoded_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class GeocodingFailure:
    address: str
    reason: str
    failure_type: str
    news_id: Optional[str] = None
    failed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
