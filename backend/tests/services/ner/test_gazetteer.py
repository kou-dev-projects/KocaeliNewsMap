import pytest
from app.services.ner.gazetteer import GazetteerMatcher


@pytest.fixture
def matcher():
    return GazetteerMatcher()


def test_exact_match(matcher):
    result = matcher.match("İzmit")
    assert result is not None
    assert result.canonical_name == "İzmit"
    assert result.match_type == "exact"
    assert result.confidence == 1.0


def test_normalized_match(matcher):
    result = matcher.match("izmit")
    assert result is not None
    assert result.canonical_name == "İzmit"
    assert result.match_type == "normalized"


def test_morphology_match(matcher):
    result = matcher.match("Çayırova'daki")
    assert result is not None
    assert result.canonical_name == "Çayırova"


def test_no_match_unknown(matcher):
    result = matcher.match("Ankara")
    assert result is None


def test_all_13_districts(matcher):
    districts = [
        "İzmit", "Gebze", "Darıca", "Gölcük", "Hereke", "Körfez",
        "Kartepe", "Başiskele", "Çayırova", "Dilovası",
        "Kandıra", "Karamürsel", "Derince",
    ]
    for d in districts:
        result = matcher.match(d)
        assert result is not None, f"{d} gazetteer'de bulunamadı"


def test_match_all_batch(matcher):
    tokens = ["İzmit", "Gebze", "Bilinmeyen"]
    results = matcher.match_all(tokens)
    assert len(results) == 2