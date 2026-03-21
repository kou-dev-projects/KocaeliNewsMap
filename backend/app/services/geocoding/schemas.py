from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone


@dataclass(frozen=True)
class GeocodingInput:
    
    address: str
    district_hint: Optional[str] = None   # BERTurk NER'den — sorguyu güçlendirir
    news_id: Optional[str] = None         # Hangi habere ait — metrics ve log için

    def normalized(self) -> str:
       
        base = self.address.strip().lower()
        # Türkçe büyük/küçük harf sorunları
        base = base.replace("İ", "i").replace("I", "ı")
        
        if self.district_hint and self.district_hint.lower() not in base:
            base = f"{base}, {self.district_hint.lower()}"
        if "kocaeli" not in base:
            base = f"{base}, kocaeli, turkey"
        return base

    def query_string(self) -> str:
        """Nominatim'e gönderilecek ham sorgu."""
        parts = [self.address.strip()]
        if self.district_hint and self.district_hint not in self.address:
            parts.append(self.district_hint)
        if "Kocaeli" not in self.address:
            parts.append("Kocaeli")
        return ", ".join(parts)


@dataclass(frozen=True)
class GeocodingResult:
    
    address: str
    lat: float
    lng: float
    display_name: str
    confidence: float           # 0.0–1.0
    source: str                 # "nominatim" | "opencage" | "cache" | "mock"
    provider_version: str       # "nominatim@1.0" — provider upgrade tespiti için
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