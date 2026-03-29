from typing import Protocol, runtime_checkable
from ..schemas import GeocodingInput, GeocodingResult


@runtime_checkable
class GeocodingProvider(Protocol):
    @property
    def name(self) -> str: ...

    def geocode(self, input_data: GeocodingInput) -> GeocodingResult | None: ...