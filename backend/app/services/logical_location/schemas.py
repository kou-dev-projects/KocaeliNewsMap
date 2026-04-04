from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services.geocoding.schemas import GeocodingInput


@dataclass(frozen=True)
class LogicalLocationCandidate:
    address: str
    location_text: str
    strategy: str
    geocode_status: str = "approximate"
    district_hint: Optional[str] = None
    neighborhood: Optional[str] = None

    def to_geocoding_input(self, *, news_id: str | None = None) -> GeocodingInput:
        return GeocodingInput(
            address=self.address,
            district_hint=self.district_hint,
            neighborhood=self.neighborhood,
            news_id=news_id,
        )
