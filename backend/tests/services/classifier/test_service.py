import pytest
from app.services.classifier import build_classifier_service
from app.services.classifier.schemas import (
    ClassificationInput, NewsCategory
)


@pytest.fixture
def svc():
    return build_classifier_service()   # mock mod — embedding yok


def test_yangin_classified(svc):
    r = svc.classify(ClassificationInput(
        title="Gebze'de fabrika yangını",
        content="İtfaiye ekipleri olay yerine sevk edildi. Duman yükseliyor."
    ))
    assert r.category == NewsCategory.YANGIN


def test_trafik_classified(svc):
    r = svc.classify(ClassificationInput(
        title="D100'de zincirleme kaza 3 yaralı"
    ))
    assert r.category == NewsCategory.TRAFIK_KAZASI


def test_elektrik_classified(svc):
    r = svc.classify(ClassificationInput(
        title="KKEDAŞ'tan kesinti uyarısı",
        summary="İzmit'te elektrik kesintisi yaşanacak"
    ))
    assert r.category == NewsCategory.ELEKTRIK_KESINTISI


def test_unknown_returns_unknown_or_closest(svc):
    r = svc.classify(ClassificationInput(title="Kocaeli'de yeni köprü açıldı"))
    assert r.category in NewsCategory.__members__.values()
    assert r.confidence >= 0.0


def test_result_has_method(svc):
    r = svc.classify(ClassificationInput(title="Yangın çıktı"))
    assert r.method in ("keyword", "semantic", "semantic_mock",
                        "resolver_agree", "resolver_keyword", "resolver_priority")


def test_news_id_propagated(svc):
    r = svc.classify(ClassificationInput(
        title="Test haberi", news_id="haber_001"
    ))
    assert r.news_id == "haber_001"


def test_all_5_categories_classifiable(svc):
    cases = [
        ("Trafik kazası D100'de 2 araç çarpıştı yaralı var", NewsCategory.TRAFIK_KAZASI),
        ("Yangın itfaiye müdahale etti duman yükseliyor", NewsCategory.YANGIN),
        ("Hırsız suçüstü yakalandı gözaltına alındı", NewsCategory.HIRSIZLIK),
        ("Elektrik kesintisi KKEDAŞ trafo arızası", NewsCategory.ELEKTRIK_KESINTISI),
        ("Festival konser tiyatro etkinlik kutlama", NewsCategory.KULTUREL_ETKINLIK),
    ]
    for title, expected in cases:
        r = svc.classify(ClassificationInput(title=title))
        assert r.category == expected, f"'{title}' → beklenen {expected}, gelen {r.category}"