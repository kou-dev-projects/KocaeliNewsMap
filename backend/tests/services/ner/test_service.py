import pytest
from app.services.ner import build_ner_service
from app.services.ner.config import NERConfig
from app.services.ner.schemas import NERInput


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
    result = svc.extract_locations(NERInput(
        title="İzmit ve Gebze'de elektrik kesintisi"
    ))
    assert "İzmit" in result.validated_districts
    assert "Gebze" in result.validated_districts


def test_result_has_provider(svc):
    result = svc.extract_locations(NERInput(title="İzmit haberi"))
    assert result.provider == "mock-ner"


def test_location_candidates_populated(svc):
    result = svc.extract_locations(NERInput(title="Körfez'de yangın"))
    assert len(result.location_candidates) > 0