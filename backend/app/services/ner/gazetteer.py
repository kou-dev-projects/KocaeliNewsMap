from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional

from .districts import (
    KOCAELI_DISTRICTS,
    normalize_for_compare,
    recover_district_name,
)
from .morphology import generate_candidates

logger = logging.getLogger(__name__)

_FUZZY_THRESHOLD = 94
_FUZZY_MIN_LEN = 6

try:
    from rapidfuzz import fuzz, process
    _FUZZY_AVAILABLE = True
except ImportError:
    _FUZZY_AVAILABLE = False
    logger.warning(
        "ner.gazetteer.fuzzy_unavailable",
        extra={"reason": "rapidfuzz kurulu değil — sadece exact match"},
    )


@dataclass(frozen=True)
class GazetteerMatch:

    original_text: str
    canonical_name: str
    match_type: str
    confidence: float


class GazetteerMatcher:
  

    def __init__(self) -> None:
        # Normalized key → canonical name mapping
        self._normalized_map: dict[str, str] = {
            normalize_for_compare(canonical): canonical
            for canonical in KOCAELI_DISTRICTS.values()
        }
        # Fuzzy match için aday listesi
        self._canonical_names = list(KOCAELI_DISTRICTS.values())

    def match(self, text: str) -> Optional[GazetteerMatch]:
       
        # Her aday için tüm katmanları dene
        candidates = generate_candidates(text)

        for candidate in candidates:
            result = self._match_single(candidate, text)
            if result:
                return result

        return None

    def _match_single(
        self, candidate: str, original: str
    ) -> Optional[GazetteerMatch]:
        

        # 1) Exact match
        if candidate in self._canonical_names:
            return GazetteerMatch(
                original_text=original,
                canonical_name=candidate,
                match_type="exact",
                confidence=1.0,
            )

        # 2) Normalized match
        norm = normalize_for_compare(candidate)
        if norm in self._normalized_map:
            return GazetteerMatch(
                original_text=original,
                canonical_name=self._normalized_map[norm],
                match_type="normalized",
                confidence=0.95,
            )

        # 3) recover_district_name (suffix-aware)
        recovered = recover_district_name(candidate)
        if recovered:
            return GazetteerMatch(
                original_text=original,
                canonical_name=recovered,
                match_type="morphology",
                confidence=0.90,
            )

        # 4) Fuzzy match
        if (
            _FUZZY_AVAILABLE
            and len(norm) >= _FUZZY_MIN_LEN
            and " " not in norm
            and norm.isalpha()
        ):
            normalized_choices = [
                normalize_for_compare(n) for n in self._canonical_names
            ]
            result = process.extractOne(
                norm,
                normalized_choices,
                scorer=fuzz.ratio,
                score_cutoff=_FUZZY_THRESHOLD,
            )
            if result:
                matched_norm, score, idx = result

                # Çok alakasız kelimeleri district'e çevirmesin.
                if matched_norm[:3] != norm[:3]:
                    return None
                if abs(len(matched_norm) - len(norm)) > 2:
                    return None

                canonical = self._canonical_names[idx]
                logger.debug(
                    "ner.gazetteer.fuzzy_match",
                    extra={
                        "original": original,
                        "matched": canonical,
                        "score": score,
                    },
                )
                return GazetteerMatch(
                    original_text=original,
                    canonical_name=canonical,
                    match_type="fuzzy",
                    confidence=score / 100.0,
                )

        return None

    def match_all(self, tokens: list[str]) -> list[GazetteerMatch]:
      
        results = []
        for token in tokens:
            match = self.match(token)
            if match:
                results.append(match)
        return results