from __future__ import annotations

import logging
import re
from typing import Optional

from .districts import recover_district_name
from .gazetteer import GazetteerMatcher
from .normalizer import normalize_location_text
from .providers.base import NERProvider
from .schemas import LocationCandidate, NERInput, NERResult, RawEntity

logger = logging.getLogger(__name__)


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

        gazetteer_matches = self._gazetteer_pass(text)

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
            gazetteer_matches,
            ner_entities,
        )

        logger.info(
            "ner.service.result",
            extra={
                "gazetteer_hits": len(gazetteer_matches),
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
        tokens = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşüâîûÂÎÛ']+", sanitized)
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
                        is_kocaeli_district=True,
                        district=match.canonical_name,
                    )
                )

        if candidates:
            return candidates

        fallback = self._district_fallback_pass(tokens)
        return [fallback] if fallback else []

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
        gazetteer_candidates: list[LocationCandidate],
        ner_entities: list[RawEntity],
    ) -> tuple[list[LocationCandidate], list[str]]:
        all_candidates: list[LocationCandidate] = list(gazetteer_candidates)
        validated: list[str] = [c.district for c in gazetteer_candidates if c.district]
        seen = set(validated)

        for entity in ner_entities:
            if not self._is_location_entity(entity):
                continue
            if entity.score < self._min_score:
                continue

            normalized = normalize_location_text(entity.text)
            district = recover_district_name(normalized)

            if district and district not in seen:
                seen.add(district)
                validated.append(district)
                all_candidates.append(
                    LocationCandidate(
                        original_text=entity.text,
                        normalized_text=normalized,
                        score=entity.score,
                        is_kocaeli_district=True,
                        district=district,
                    )
                )
            elif not district:
                neighborhood = self._extract_neighborhood(entity.text)
                all_candidates.append(
                    LocationCandidate(
                        original_text=entity.text,
                        normalized_text=normalized,
                        score=entity.score,
                        is_kocaeli_district=False,
                        district=None,
                        neighborhood=neighborhood,
                    )
                )

        return all_candidates, validated

    def _is_location_entity(self, entity: RawEntity) -> bool:
        label = entity.label.upper()
        return label in {
            "LOC",
            "B-LOC",
            "I-LOC",
            "İL",
            "İLÇE",
            "MAHALLE",
            "MEKAN",
            "IL",
            "ILCE",
            "MAHALLE",
            "MEKAN",
        }

    @staticmethod
    def _extract_neighborhood(text: str) -> str | None:
        lower = text.lower().strip()
        keywords = [
            "mahallesi",
            "mahalle",
            "mah.",
            "mah",
            "sokak",
            "sok.",
            "cadde",
            "caddesi",
            "cad.",
            "bulvarı",
            "bulvar",
            "blv.",
        ]
        for keyword in keywords:
            if keyword in lower:
                return text.strip()
        return None
