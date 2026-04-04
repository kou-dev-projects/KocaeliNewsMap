from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NERInput:
    title: str
    summary: Optional[str] = None
    content: Optional[str] = None

    def build_text_payload(self) -> str:
        parts = [self.title]

        if self.summary:
            parts.append(self.summary)

        if self.content:
            parts.append(self.content[:4000])

        return "\n".join(part.strip() for part in parts if part and part.strip())


@dataclass(frozen=True)
class RawEntity:
    text: str
    label: str
    score: float
    start: Optional[int] = None
    end: Optional[int] = None


@dataclass(frozen=True)
class LocationCandidate:
    original_text: str
    normalized_text: str
    score: float
    is_kocaeli_district: bool
    district: Optional[str] = None
    neighborhood: Optional[str] = None
    feature_type: Optional[str] = None
    source_key: Optional[str] = None


@dataclass(frozen=True)
class NERResult:
    raw_entities: list[RawEntity]
    location_candidates: list[LocationCandidate]
    validated_districts: list[str]
    provider: str
