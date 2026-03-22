from __future__ import annotations

from .districts import recover_district_name
from .normalizer import normalize_location_text
from .providers.base import NERProvider
from .schemas import LocationCandidate, NERInput, NERResult, RawEntity


class NERService:
    def __init__(
        self,
        provider: NERProvider,
        min_score: float = 0.50,
    ) -> None:
        self._provider = provider
        self._min_score = min_score

    def extract_locations(self, input_data: NERInput) -> NERResult:
        text = input_data.build_text_payload()

        if not text.strip():
            return NERResult(
                raw_entities=[],
                location_candidates=[],
                validated_districts=[],
                provider=self._provider.name,
            )

        raw_entities = self._provider.extract_entities(text)

        location_candidates: list[LocationCandidate] = []
        validated_districts: list[str] = []
        seen_districts: set[str] = set()

        for entity in raw_entities:
            if not self._is_location_entity(entity):
                continue

            if entity.score < self._min_score:
                continue

            normalized_text = normalize_location_text(entity.text)
            district = recover_district_name(normalized_text)
            is_kocaeli = district is not None

            candidate = LocationCandidate(
                original_text=entity.text,
                normalized_text=normalized_text,
                score=entity.score,
                is_kocaeli_district=is_kocaeli,
                district=district,
            )
            location_candidates.append(candidate)

            if district and district not in seen_districts:
                seen_districts.add(district)
                validated_districts.append(district)

        return NERResult(
            raw_entities=raw_entities,
            location_candidates=location_candidates,
            validated_districts=validated_districts,
            provider=self._provider.name,
        )

    def _is_location_entity(self, entity: RawEntity) -> bool:
        label = entity.label.upper()
        return label in {"LOC", "B-LOC", "I-LOC"}
