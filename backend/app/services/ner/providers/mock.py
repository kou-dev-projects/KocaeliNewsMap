from __future__ import annotations

import re

from ..schemas import RawEntity


class MockNERProvider:
    name = "mock-ner"

    _KNOWN_LOCATIONS = (
        "İzmit",
        "Gebze",
        "Darıca",
        "Gölcük",
        "Körfez",
        "Kartepe",
        "Başiskele",
        "Çayırova",
        "Dilovası",
        "Kandıra",
        "Karamürsel",
        "Derince",
    )

    def extract_entities(self, text: str) -> list[RawEntity]:
        if not text.strip():
            return []

        entities: list[RawEntity] = []

        for location in self._KNOWN_LOCATIONS:
            pattern = re.compile(rf"\b{re.escape(location)}(?:['’][a-zA-ZçğıöşüÇĞİÖŞÜ]+)?\b", re.IGNORECASE)

            for match in pattern.finditer(text):
                entities.append(
                    RawEntity(
                        text=match.group(0),
                        label="LOC",
                        score=0.99,
                        start=match.start(),
                        end=match.end(),
                    )
                )

        return entities
