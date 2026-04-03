from __future__ import annotations

import logging
import re
from typing import Optional

from .districts import (
    KOCAELI_DISTRICTS,
    normalize_for_compare,
    recover_alias_district_name,
    recover_district_name,
)
from .gazetteer import GazetteerMatcher
from .normalizer import normalize_location_text
from .providers.base import NERProvider
from .schemas import LocationCandidate, NERInput, NERResult, RawEntity

logger = logging.getLogger(__name__)

_PRECISE_LOCATION_KEYWORDS = (
    "mahallesi",
    "mahalle",
    "mah.",
    "mah",
    "sokak",
    "sok.",
    "cadde",
    "caddesi",
    "cad.",
    "bulvari",
    "bulvar",
    "blv.",
    "baraji",
    "goleti",
    "tesisi",
    "aritma tesisi",
    "icmesuyu",
    "isale hatti",
    "iletim hatti",
    "tuneli",
    "hastanesi",
    "liman yolu",
    "cezaevi",
    "stadyumu",
    "terminali",
    "kampusu",
    "golu",
    "meydani",
    "kavsagi",
    "otoyolu",
)

_HEURISTIC_NOISE_TOKENS = {
    "acilis",
    "acildi",
    "etkilendi",
    "gibi",
    "icin",
    "ile",
    "ilcesindeki",
    "karsiliyor",
    "olan",
    "oldu",
    "olarak",
    "su",
    "ve",
    "yapildi",
}

_DISTRICT_PRECEDENCE: dict[str, set[str]] = {
    "hereke": {"korfez"},
}


class NERService:
    def __init__(
        self,
        provider: NERProvider,
        min_score: float = 0.50,
        gazetteer: Optional[GazetteerMatcher] = None,
    ) -> None:
        self._provider = provider
        self._min_score = min_score
        self._gazetteer = gazetteer or GazetteerMatcher()

    def extract_locations(self, input_data: NERInput) -> NERResult:
        text = input_data.build_text_payload()

        if not text.strip():
            return NERResult(
                raw_entities=[],
                location_candidates=[],
                validated_districts=[],
                provider=self._provider.name,
            )

        title_district_hints = self._extract_title_district_hints(input_data.title)
        gazetteer_matches = self._gazetteer_pass(text)
        heuristic_matches = self._heuristic_location_pass(text)

        try:
            ner_entities = self._provider.extract_entities(text)
        except Exception as exc:
            logger.warning(
                "ner.service.provider_failed",
                extra={
                    "provider": self._provider.name,
                    "error": f"{type(exc).__name__}: {exc}",
                    "gazetteer_hits": len(gazetteer_matches),
                },
            )
            ner_entities = []

        location_candidates, validated_districts = self._merge_and_validate(
            [*gazetteer_matches, *heuristic_matches],
            ner_entities,
        )
        location_candidates = self._sort_candidates(location_candidates)
        validated_districts = self._finalize_validated_districts(
            validated_districts=validated_districts,
            title_district_hints=title_district_hints,
        )

        logger.info(
            "ner.service.result",
            extra={
                "gazetteer_hits": len(gazetteer_matches),
                "heuristic_hits": len(heuristic_matches),
                "ner_hits": len(ner_entities),
                "validated_districts": validated_districts,
            },
        )

        return NERResult(
            raw_entities=ner_entities,
            location_candidates=location_candidates,
            validated_districts=validated_districts,
            provider=self._provider.name,
        )

    def _gazetteer_pass(self, text: str) -> list[LocationCandidate]:
        sanitized = text.replace("\u2019", "'")
        tokens = re.findall(r"[A-Za-zCĞIÖŞÜcğioşüâîûÂÎÛ']+", sanitized)
        tokens = [token for token in tokens if len(token) >= 3]

        candidates: list[LocationCandidate] = []
        seen: set[str] = set()

        for span_size in (4, 3, 2, 1):
            if len(tokens) < span_size:
                continue

            for start_index in range(len(tokens) - span_size + 1):
                span = " ".join(tokens[start_index : start_index + span_size])
                match = self._gazetteer.match(span)
                if not match or match.canonical_name in seen:
                    continue

                seen.add(match.canonical_name)
                candidates.append(
                    LocationCandidate(
                        original_text=match.original_text,
                        normalized_text=match.canonical_name,
                        score=match.confidence,
                        is_kocaeli_district=match.feature_type == "district",
                        district=match.district,
                        neighborhood=(
                            match.canonical_name
                            if match.feature_type == "neighborhood"
                            else None
                        ),
                        feature_type=match.feature_type,
                        source_key=match.source_key,
                    )
                )

        if candidates:
            return candidates

        fallback = self._district_fallback_pass(tokens)
        return [fallback] if fallback else []

    def _heuristic_location_pass(self, text: str) -> list[LocationCandidate]:
        sanitized = text.replace("\u2019", "'").replace("\n", " ")
        tokens = re.findall(r"[A-Za-z0-9CĞIÖŞÜcğioşü']+", sanitized)
        candidates: list[LocationCandidate] = []
        seen: set[str] = set()

        for span_size in range(5, 1, -1):
            if len(tokens) < span_size:
                continue

            for start_index in range(len(tokens) - span_size + 1):
                span_tokens = tokens[start_index : start_index + span_size]
                if not self._looks_like_heuristic_span(span_tokens):
                    continue

                span = " ".join(span_tokens).strip()
                normalized = normalize_location_text(span)
                if not normalized:
                    continue

                compare_value = normalized.lower()
                if not any(
                    keyword in compare_value for keyword in _PRECISE_LOCATION_KEYWORDS
                ):
                    continue

                dedupe_key = normalized.casefold()
                if dedupe_key in seen:
                    continue

                district = self._recover_embedded_district(span)
                neighborhood = span.strip() if self._extract_neighborhood(span) else None
                is_exact_district = district is not None and normalize_for_compare(
                    normalized
                ) == normalize_for_compare(district)

                candidates.append(
                    LocationCandidate(
                        original_text=span,
                        normalized_text=normalized,
                        score=0.86,
                        is_kocaeli_district=is_exact_district,
                        district=district,
                        neighborhood=neighborhood,
                    )
                )
                seen.add(dedupe_key)

        return candidates

    def _district_fallback_pass(
        self,
        tokens: list[str],
    ) -> LocationCandidate | None:
        for span_size in (4, 3, 2, 1):
            if len(tokens) < span_size:
                continue

            for start_index in range(len(tokens) - span_size + 1):
                span = " ".join(tokens[start_index : start_index + span_size])
                district = recover_district_name(span)
                if not district:
                    continue

                return LocationCandidate(
                    original_text=span,
                    normalized_text=district,
                    score=0.88,
                    is_kocaeli_district=True,
                    district=district,
                )

        return None

    def _merge_and_validate(
        self,
        seed_candidates: list[LocationCandidate],
        ner_entities: list[RawEntity],
    ) -> tuple[list[LocationCandidate], list[str]]:
        all_candidates: list[LocationCandidate] = []
        validated: list[str] = []
        seen_candidate_keys: set[tuple[str, str | None, str | None]] = set()

        for candidate in seed_candidates:
            key = (
                candidate.original_text.casefold(),
                candidate.district,
                candidate.neighborhood,
            )
            if key in seen_candidate_keys:
                continue
            seen_candidate_keys.add(key)
            all_candidates.append(candidate)
            if candidate.district and candidate.district not in validated:
                validated.append(candidate.district)

        seen = set(validated)

        for entity in ner_entities:
            if not self._is_location_entity(entity):
                continue
            if entity.score < self._min_score:
                continue

            normalized = normalize_location_text(entity.text)
            district = recover_district_name(normalized)
            if district is None:
                district = self._recover_embedded_district(entity.text)

            if district and district not in seen:
                seen.add(district)
                validated.append(district)

            if district:
                candidate = LocationCandidate(
                    original_text=entity.text,
                    normalized_text=normalized,
                    score=entity.score,
                    is_kocaeli_district=normalize_for_compare(normalized)
                    == normalize_for_compare(district),
                    district=district,
                )
            else:
                candidate = LocationCandidate(
                    original_text=entity.text,
                    normalized_text=normalized,
                    score=entity.score,
                    is_kocaeli_district=False,
                    district=None,
                    neighborhood=self._extract_neighborhood(entity.text),
                )

            key = (
                candidate.original_text.casefold(),
                candidate.district,
                candidate.neighborhood,
            )
            if key not in seen_candidate_keys:
                seen_candidate_keys.add(key)
                all_candidates.append(candidate)

        return self._apply_district_precedence(all_candidates, validated)

    def _extract_title_district_hints(self, title: str) -> list[str]:
        if not title.strip():
            return []

        hints: list[str] = []
        seen: set[str] = set()

        for candidate in self._gazetteer_pass(title):
            if not candidate.district:
                continue
            normalized = normalize_for_compare(candidate.district)
            if normalized in seen:
                continue
            seen.add(normalized)
            hints.append(candidate.district)

        return hints

    @staticmethod
    def _apply_district_precedence(
        candidates: list[LocationCandidate],
        validated: list[str],
    ) -> tuple[list[LocationCandidate], list[str]]:
        normalized_validated = {
            normalize_for_compare(district): district for district in validated
        }
        suppressed: set[str] = set()

        for preferred, shadowed_values in _DISTRICT_PRECEDENCE.items():
            if preferred in normalized_validated:
                suppressed.update(
                    value for value in shadowed_values if value in normalized_validated
                )

        if not suppressed:
            return candidates, validated

        filtered_validated = [
            district
            for district in validated
            if normalize_for_compare(district) not in suppressed
        ]
        filtered_candidates = [
            candidate
            for candidate in candidates
            if normalize_for_compare(candidate.district or "") not in suppressed
            or candidate.neighborhood is not None
        ]
        return filtered_candidates, filtered_validated

    @staticmethod
    def _finalize_validated_districts(
        *,
        validated_districts: list[str],
        title_district_hints: list[str],
    ) -> list[str]:
        if not validated_districts:
            return []

        normalized_to_original: dict[str, str] = {}
        ordered_validated: list[str] = []
        for district in validated_districts:
            normalized = normalize_for_compare(district)
            if not normalized or normalized in normalized_to_original:
                continue
            normalized_to_original[normalized] = district
            ordered_validated.append(normalized)

        ordered_title: list[str] = []
        for district in title_district_hints:
            normalized = normalize_for_compare(district)
            if (
                normalized
                and normalized in normalized_to_original
                and normalized not in ordered_title
            ):
                ordered_title.append(normalized)

        if len(ordered_title) == 1:
            primary = ordered_title[0]
            return [normalized_to_original[primary]]

        if not ordered_title:
            return [normalized_to_original[district] for district in ordered_validated]

        prioritized = ordered_title + [
            district
            for district in ordered_validated
            if district not in ordered_title
        ]
        return [normalized_to_original[district] for district in prioritized]

    def _is_location_entity(self, entity: RawEntity) -> bool:
        label = entity.label.upper()
        if label in {
            "ORG",
            "B-ORG",
            "I-ORG",
            "FAC",
            "B-FAC",
            "I-FAC",
            "GPE",
            "B-GPE",
            "I-GPE",
        }:
            return True
        return label in {
            "LOC",
            "B-LOC",
            "I-LOC",
            "IL",
            "ILCE",
            "MAHALLE",
            "MEKAN",
            "İL",
            "İLÇE",
        }

    @staticmethod
    def _extract_neighborhood(text: str) -> str | None:
        lower = text.lower().strip()
        keywords = [
            "mahallesi",
            "mahalle",
            "mah.",
        ]
        for keyword in keywords:
            if keyword in lower:
                return text.strip()
        return None

    @staticmethod
    def _recover_embedded_district(text: str) -> str | None:
        alias_match = recover_alias_district_name(text)
        if alias_match:
            return alias_match

        normalized = normalize_for_compare(text)
        for canonical in KOCAELI_DISTRICTS.values():
            if normalized.startswith(normalize_for_compare(canonical) + " "):
                return canonical
        return None

    @staticmethod
    def _sort_candidates(
        candidates: list[LocationCandidate],
    ) -> list[LocationCandidate]:
        def sort_key(candidate: LocationCandidate) -> tuple[int, int, int, int, float, int, str]:
            normalized = normalize_for_compare(candidate.original_text)
            tokens = [part for part in normalized.split() if part]
            token_count = len(tokens)
            has_precise_keyword = any(
                keyword in normalized for keyword in _PRECISE_LOCATION_KEYWORDS
            )
            has_noise = any(token in _HEURISTIC_NOISE_TOKENS for token in tokens)
            long_span_penalty = 1 if token_count > 4 else 0

            if has_precise_keyword or candidate.neighborhood:
                specificity_rank = 0
            elif not candidate.is_kocaeli_district:
                specificity_rank = 1
            else:
                specificity_rank = 2

            return (
                specificity_rank,
                -token_count,
                1 if has_noise else 0,
                long_span_penalty,
                -candidate.score,
                token_count,
                candidate.original_text.casefold(),
            )

        return sorted(candidates, key=sort_key)

    @staticmethod
    def _looks_like_heuristic_span(tokens: list[str]) -> bool:
        if not tokens or len(tokens) > 5:
            return False

        normalized_tokens = [
            normalize_location_text(token).lower()
            for token in tokens
            if normalize_location_text(token)
        ]
        if not normalized_tokens:
            return False

        if any(token in _HEURISTIC_NOISE_TOKENS for token in normalized_tokens):
            return False

        if any(
            token and token[0].isalpha() and token[0].islower()
            for token in tokens
        ):
            return False

        last_token = normalized_tokens[-1]
        last_two_tokens = (
            " ".join(normalized_tokens[-2:])
            if len(normalized_tokens) >= 2
            else ""
        )

        return (
            last_token in _PRECISE_LOCATION_KEYWORDS
            or last_two_tokens in _PRECISE_LOCATION_KEYWORDS
        )
