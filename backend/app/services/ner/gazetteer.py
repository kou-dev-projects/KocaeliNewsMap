from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .districts import normalize_for_compare, recover_district_name
from .gazetteer_catalog import GazetteerEntry, build_entries
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
        extra={"reason": "rapidfuzz kurulu degil - sadece exact match"},
    )


@dataclass(frozen=True)
class GazetteerMatch:
    original_text: str
    canonical_name: str
    match_type: str
    confidence: float
    feature_type: str
    district: Optional[str]
    source_key: Optional[str] = None


class GazetteerMatcher:
    def __init__(self) -> None:
        self._entries = build_entries()
        self._district_entry_map: dict[str, GazetteerEntry] = {
            entry.canonical_name: entry
            for entry in self._entries
            if entry.feature_type == "district"
        }
        self._exact_alias_map: dict[str, GazetteerEntry] = {}
        self._normalized_alias_map: dict[str, GazetteerEntry] = {}
        self._fuzzy_choices: list[str] = []
        self._fuzzy_entries: list[GazetteerEntry] = []

        for entry in self._entries:
            for alias in entry.aliases:
                self._exact_alias_map[alias] = entry
                self._normalized_alias_map[normalize_for_compare(alias)] = entry
                if entry.allow_fuzzy:
                    self._fuzzy_choices.append(normalize_for_compare(alias))
                    self._fuzzy_entries.append(entry)

    def match(self, text: str) -> Optional[GazetteerMatch]:
        candidates = generate_candidates(text)
        for candidate in candidates:
            result = self._match_single(candidate, text)
            if result:
                return result
        return None

    def _match_single(self, candidate: str, original: str) -> Optional[GazetteerMatch]:
        entry = self._exact_alias_map.get(candidate)
        if entry is not None:
            return self._build_match(original, entry, "exact", 1.0)

        normalized = normalize_for_compare(candidate)
        entry = self._normalized_alias_map.get(normalized)
        if entry is not None:
            return self._build_match(original, entry, "normalized", 0.95)

        recovered = recover_district_name(candidate)
        if recovered:
            recovered_entry = self._district_entry_map.get(recovered)
            if recovered_entry is not None:
                return self._build_match(original, recovered_entry, "morphology", 0.90)

        if (
            _FUZZY_AVAILABLE
            and len(normalized) >= _FUZZY_MIN_LEN
            and " " not in normalized
            and normalized.isalpha()
        ):
            result = process.extractOne(
                normalized,
                self._fuzzy_choices,
                scorer=fuzz.ratio,
                score_cutoff=_FUZZY_THRESHOLD,
            )
            if result:
                matched_norm, score, idx = result
                if matched_norm[:3] != normalized[:3]:
                    return None
                if abs(len(matched_norm) - len(normalized)) > 2:
                    return None
                return self._build_match(
                    original,
                    self._fuzzy_entries[idx],
                    "fuzzy",
                    score / 100.0,
                )

        return None

    def _build_match(
        self,
        original: str,
        entry: GazetteerEntry,
        match_type: str,
        confidence: float,
    ) -> GazetteerMatch:
        return GazetteerMatch(
            original_text=original,
            canonical_name=entry.canonical_name,
            match_type=match_type,
            confidence=confidence,
            feature_type=entry.feature_type,
            district=entry.district,
            source_key=entry.source_key,
        )

    def match_all(self, tokens: list[str]) -> list[GazetteerMatch]:
        results = []
        for token in tokens:
            match = self.match(token)
            if match:
                results.append(match)
        return results
