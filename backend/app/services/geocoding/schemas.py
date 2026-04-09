from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.services.ner.districts import normalize_for_compare as _shared_normalize_for_compare


def _normalize_for_compare(value: str) -> str:
    return _shared_normalize_for_compare(value)


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
        normalized_neighborhood = (
            _normalize_for_compare(self.neighborhood) if self.neighborhood else None
        )
        normalized_address = _normalize_for_compare(self.address)

        if (
            self.neighborhood
            and normalized_neighborhood
            and normalized_neighborhood not in normalized_address
        ):
            parts.append(self.neighborhood.strip())
        if not parts or normalized_neighborhood != normalized_address:
            parts.append(self.address.strip())

        address_norm = _normalize_for_compare(self.address)
        hint_norm = (
            _normalize_for_compare(self.district_hint) if self.district_hint else None
        )

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
