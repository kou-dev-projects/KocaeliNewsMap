import pytest

from app.services.ner import build_ner_service
from app.services.ner.config import NERConfig
from app.services.ner.districts import normalize_for_compare
from app.services.ner.schemas import NERInput, RawEntity
from app.services.ner.service import NERService


@pytest.fixture
def svc():
    cfg = NERConfig(provider="mock", min_score=0.5, model_name="")
    return build_ner_service(cfg)


def test_izmit_extracted(svc):
    result = svc.extract_locations(NERInput(title="Izmit'te trafik kazasi"))
    assert "izmit" in {
        normalize_for_compare(value) for value in result.validated_districts
    }


def test_gebze_extracted(svc):
    result = svc.extract_locations(NERInput(title="Gebze'de fabrika yangini"))
    assert "gebze" in {
        normalize_for_compare(value) for value in result.validated_districts
    }


def test_cayirova_with_suffix(svc):
    result = svc.extract_locations(NERInput(title="Cayirova'daki kazada 2 yarali"))
    assert "cayirova" in {
        normalize_for_compare(value) for value in result.validated_districts
    }


def test_empty_title(svc):
    result = svc.extract_locations(NERInput(title=""))
    assert result.validated_districts == []


def test_no_kocaeli_location(svc):
    result = svc.extract_locations(NERInput(title="Ankara'da hava durumu"))
    assert result.validated_districts == []


def test_multiple_districts(svc):
    result = svc.extract_locations(
        NERInput(title="Izmit ve Gebze'de elektrik kesintisi")
    )
    normalized = {normalize_for_compare(value) for value in result.validated_districts}
    assert "izmit" in normalized
    assert "gebze" in normalized


def test_result_has_provider(svc):
    result = svc.extract_locations(NERInput(title="Izmit haberi"))
    assert result.provider == "mock-ner"


def test_location_candidates_populated(svc):
    result = svc.extract_locations(NERInput(title="Korfez'de yangin"))
    assert len(result.location_candidates) > 0


class StubProvider:
    @property
    def name(self):
        return "stub-ner"

    def extract_entities(self, text: str):
        return [
            RawEntity(text="Izmit", label="LOC", score=0.9),
            RawEntity(text="Cumhuriyet Mahallesi", label="LOC", score=0.9),
        ]


def test_neighborhood_does_not_inherit_previous_district():
    service = NERService(provider=StubProvider(), min_score=0.5)

    result = service.extract_locations(
        NERInput(title="Izmit'te olay yasandi. Cumhuriyet Mahallesi etkilendi.")
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

    result = service.extract_locations(NERInput(title="Gebze'de fabrika yangini"))

    assert "gebze" in {
        normalize_for_compare(value) for value in result.validated_districts
    }
    assert any(
        normalize_for_compare(candidate.district or "") == "gebze"
        for candidate in result.location_candidates
    )


def test_multiword_alias_is_detected_when_provider_fails():
    service = NERService(provider=ExplodingProvider(), min_score=0.5)

    result = service.extract_locations(
        NERInput(
            title="Yahya Kaptan mahallesinde trafik kazasi",
            content="Yahya Kaptan mahallesinde iki arac carpisti.",
        )
    )

    assert "izmit" in {
        normalize_for_compare(value) for value in result.validated_districts
    }
    assert any(
        normalize_for_compare(candidate.district or "") == "izmit"
        for candidate in result.location_candidates
    )


def test_hereke_stays_validated_as_hereke():
    service = NERService(provider=ExplodingProvider(), min_score=0.5)

    result = service.extract_locations(
        NERInput(title="Hereke'de etkinlik duzenlendi")
    )

    assert "hereke" in {
        normalize_for_compare(value) for value in result.validated_districts
    }
    assert any(
        candidate.feature_type == "district"
        and normalize_for_compare(candidate.district or "") == "hereke"
        for candidate in result.location_candidates
    )


def test_hereke_suppresses_korfez_when_both_detected():
    service = NERService(provider=ExplodingProvider(), min_score=0.5)

    result = service.extract_locations(
        NERInput(
            title="Herekede yarin icin elektrik kesintisi planlandi",
            content="Korfez Hereke bolgesinde yarin planli elektrik kesintisi uygulanacak.",
        )
    )

    normalized = {
        normalize_for_compare(value) for value in result.validated_districts
    }

    assert "hereke" in normalized
    assert "korfez" not in normalized


def test_title_primary_district_suppresses_body_secondary_districts():
    service = NERService(provider=ExplodingProvider(), min_score=0.5)

    result = service.extract_locations(
        NERInput(
            title="Yuvacik Baraji doldu, kapaklar acildi",
            content="Kandira hattindaki Namazgah Baraji da gundeme geldi.",
        )
    )

    assert [normalize_for_compare(value) for value in result.validated_districts] == [
        "basiskele"
    ]


class PreciseLocationProvider:
    @property
    def name(self):
        return "precise-ner"

    def extract_entities(self, text: str):
        return [
            RawEntity(text="Ihsaniye Baraji", label="ORG", score=0.99),
            RawEntity(
                text="Karamursel Icmesuyu Aritma Tesisi",
                label="ORG",
                score=0.91,
            ),
            RawEntity(text="Karamursel", label="LOC", score=0.95),
        ]


def test_precise_location_candidates_rank_before_noisy_heuristics():
    service = NERService(provider=PreciseLocationProvider(), min_score=0.5)

    result = service.extract_locations(
        NERInput(
            title="Ihsaniye Baraji ve Karamursel Icmesuyu Aritma Tesisi icin acilis yapildi",
            content="Karamursel ilcesindeki proje su ihtiyacini karsiliyor.",
        )
    )

    top_candidates = [
        candidate.original_text for candidate in result.location_candidates[:3]
    ]

    assert "Ihsaniye Baraji" in top_candidates
    assert "Karamursel Icmesuyu Aritma Tesisi" in top_candidates
    assert top_candidates[0] != "Karamursel"
