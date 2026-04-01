import pytest

from app.services.ner import build_ner_service
from app.services.ner.config import NERConfig
from app.services.ner.schemas import NERInput, RawEntity
from app.services.ner.service import NERService


@pytest.fixture
def svc():
    cfg = NERConfig(provider="mock", min_score=0.5, model_name="")
    return build_ner_service(cfg)


def test_izmit_extracted(svc):
    result = svc.extract_locations(NERInput(title="İzmit'te trafik kazası"))
    assert "İzmit" in result.validated_districts


def test_gebze_extracted(svc):
    result = svc.extract_locations(NERInput(title="Gebze'de fabrika yangını"))
    assert "Gebze" in result.validated_districts


def test_cayirova_with_suffix(svc):
    result = svc.extract_locations(NERInput(title="Çayırova'daki kazada 2 yaralı"))
    assert "Çayırova" in result.validated_districts


def test_empty_title(svc):
    result = svc.extract_locations(NERInput(title=""))
    assert result.validated_districts == []


def test_no_kocaeli_location(svc):
    result = svc.extract_locations(NERInput(title="Ankara'da hava durumu"))
    assert result.validated_districts == []


def test_multiple_districts(svc):
    result = svc.extract_locations(
        NERInput(title="İzmit ve Gebze'de elektrik kesintisi")
    )
    assert "İzmit" in result.validated_districts
    assert "Gebze" in result.validated_districts


def test_result_has_provider(svc):
    result = svc.extract_locations(NERInput(title="İzmit haberi"))
    assert result.provider == "mock-ner"


def test_location_candidates_populated(svc):
    result = svc.extract_locations(NERInput(title="Körfez'de yangın"))
    assert len(result.location_candidates) > 0


class StubProvider:
    @property
    def name(self):
        return "stub-ner"

    def extract_entities(self, text: str):
        return [
            RawEntity(text="İzmit", label="LOC", score=0.9),
            RawEntity(text="Cumhuriyet Mahallesi", label="LOC", score=0.9),
        ]


def test_neighborhood_does_not_inherit_previous_district():
    service = NERService(provider=StubProvider(), min_score=0.5)

    result = service.extract_locations(
        NERInput(title="İzmit'te olay yaşandı. Cumhuriyet Mahallesi etkilendi.")
    )

    neighborhood_candidate = next(
        candidate
        for candidate in result.location_candidates
        if candidate.neighborhood == "Cumhuriyet Mahallesi"
    )

    assert neighborhood_candidate.district is None


class ExplodingProvider:
    @property
    def name(self):
        return "exploding-ner"

    def extract_entities(self, text: str):
        raise RuntimeError("provider unavailable")


def test_gazetteer_results_survive_provider_failure():
    service = NERService(provider=ExplodingProvider(), min_score=0.5)

    result = service.extract_locations(
        NERInput(title="Gebze'de fabrika yangını")
    )

    assert "Gebze" in result.validated_districts
    assert any(candidate.district == "Gebze" for candidate in result.location_candidates)


def test_multiword_alias_is_detected_when_provider_fails():
    service = NERService(provider=ExplodingProvider(), min_score=0.5)

    result = service.extract_locations(
        NERInput(
            title="Yahya Kaptan mahallesinde trafik kazası",
            content="Yahya Kaptan mahallesinde iki araç çarpıştı.",
        )
    )

    assert "İzmit" in result.validated_districts
    assert any(candidate.district == "İzmit" for candidate in result.location_candidates)
