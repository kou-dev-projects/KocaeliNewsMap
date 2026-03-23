from __future__ import annotations
import re

from ..gazetteer import GazetteerMatcher
from ..schemas import RawEntity


class FuzzyGazetteerProvider:

    name = "fuzzy-gazetteer"

    def __init__(self) -> None:
        self._matcher = GazetteerMatcher()

    def extract_entities(self, text: str) -> list[RawEntity]:
        if not text.strip():
            return []

        tokens = self._tokenize(text)
        entities: list[RawEntity] = []
        seen: set[str] = set()

        for token in tokens:
            if len(token) < 3:
                continue

            match = self._matcher.match(token)
            if match and match.canonical_name not in seen:
                seen.add(match.canonical_name)
                entities.append(
                    RawEntity(
                        text=match.original_text,
                        label="LOC",
                        score=match.confidence,
                    )
                )

        return entities

    def _tokenize(self, text: str) -> list[str]:
 
        raw = re.split(r"[\s,;:.!?()\[\]\"\"]+", text)
        tokens = [t for t in raw if t]

        # Büyük harfle başlayanlar önce — yer adı olasılığı yüksek
        prioritized = [t for t in tokens if t and t[0].isupper()]
        rest = [t for t in tokens if t and not t[0].isupper()]

        return prioritized + rest