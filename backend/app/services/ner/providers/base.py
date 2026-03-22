from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..schemas import RawEntity


@runtime_checkable
class NERProvider(Protocol):
    @property
    def name(self) -> str:
        ...

    def extract_entities(self, text: str) -> list[RawEntity]:
        ...
