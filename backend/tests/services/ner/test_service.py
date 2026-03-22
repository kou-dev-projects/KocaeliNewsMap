from app.services.ner.providers.mock import MockNERProvider
from app.services.ner.schemas import NERInput
from app.services.ner.service import NERService
from app.services.ner.schemas import RawEntity

def build_service() -> NERService:
    return NERService(
        provider=MockNERProvider(),
        min_score=0.50,
    )


def test_extract_locations_returns_validated_districts():
    service = build_service()

    result = service.extract_locations(
        NERInput(
            title="Gebze'de trafik kazası",
            content="Kaza sonrası ekipler olay yerine sevk edildi.",
        )
    )

    assert "Gebze" in result.validated_districts
    assert result.provider == "mock-ner"


def test_extract_locations_deduplicates_same_district():
    service = build_service()

    result = service.extract_locations(
        NERInput(
            title="İzmit'te yangın",
            content="İzmit'te çıkan yangına müdahale edildi. İzmit'te trafik aksadı.",
        )
    )

    assert result.validated_districts == ["İzmit"]


def test_extract_locations_ignores_blank_input():
    service = build_service()

    result = service.extract_locations(
        NERInput(
            title="   ",
            content="   ",
        )
    )

    assert result.raw_entities == []
    assert result.location_candidates == []
    assert result.validated_districts == []


def test_extract_locations_marks_non_kocaeli_as_invalid():
    service = build_service()

    result = service.extract_locations(
        NERInput(
            title="İstanbul'da toplantı",
            content="Toplantı sonrası açıklama yapıldı.",
        )
    )

    assert result.validated_districts == []


def test_extract_locations_keeps_location_candidates():
    service = build_service()

    result = service.extract_locations(
        NERInput(
            title="Başiskele'ye yeni yatırım",
            content="Başiskele'ye yapılacak proje tanıtıldı.",
        )
    )

    assert len(result.location_candidates) >= 1
    assert result.location_candidates[0].normalized_text == "Başiskele"
    assert result.location_candidates[0].district == "Başiskele"
    assert result.location_candidates[0].is_kocaeli_district is True


class StubProvider:
    name = "stub-ner"

    def extract_entities(self, text: str):
        return [
            RawEntity(text="Gebze TEM", label="LOC", score=0.90),
            RawEntity(text="Körfez D100", label="LOC", score=0.90),
            RawEntity(text="İstanbul", label="LOC", score=0.95),
        ]

def test_extract_locations_recovers_district_from_extended_span():
    service = NERService(provider=StubProvider(), min_score=0.50)

    result = service.extract_locations(
        NERInput(title="Test", content="Test")
    )

    assert result.validated_districts == ["Gebze", "Körfez"]
