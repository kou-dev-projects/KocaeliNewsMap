import pytest

from app.services.classifier.keyword_classifier import KeywordClassifier
from app.services.classifier.schemas import ClassificationInput, NewsCategory


@pytest.fixture
def clf():
    return KeywordClassifier()


def test_yangin_keyword(clf):
    r = clf.classify(
        ClassificationInput(title="Gebze'de fabrika yangını çıktı")
    )
    assert r is not None
    assert r.category == NewsCategory.YANGIN
    assert r.confidence == 1.0
    assert "yangın" in r.matched_keywords


def test_trafik_keyword(clf):
    r = clf.classify(
        ClassificationInput(title="D100'de zincirleme trafik kazası")
    )
    assert r is not None
    assert r.category == NewsCategory.TRAFIK_KAZASI


def test_elektrik_keyword(clf):
    r = clf.classify(
        ClassificationInput(
            title="KKEDAŞ açıkladı: İzmit'te planlı kesinti"
        )
    )
    assert r is not None
    assert r.category == NewsCategory.ELEKTRIK_KESINTISI


def test_hirsizlik_keyword(clf):
    r = clf.classify(
        ClassificationInput(title="Başiskele'de hırsız yakalandı")
    )
    assert r is not None
    assert r.category == NewsCategory.HIRSIZLIK


def test_kulturel_keyword(clf):
    r = clf.classify(
        ClassificationInput(title="İzmit'te yaz festivali başladı")
    )
    assert r is not None
    assert r.category == NewsCategory.KULTUREL_ETKINLIK


def test_unknown_returns_none(clf):
    r = clf.classify(ClassificationInput(title="Kocaeli'de yeni park açıldı"))
    assert r is None


def test_conflict_trafik_yangin_priority(clf):
    r = clf.classify(
        ClassificationInput(
            title="Trafik kazasında araç alev aldı yangın çıktı"
        )
    )
    assert r is not None
    assert r.category == NewsCategory.TRAFIK_KAZASI


def test_matched_keywords_populated(clf):
    r = clf.classify(
        ClassificationInput(title="İtfaiye yangına müdahale etti")
    )
    assert r is not None
    assert len(r.matched_keywords) > 0


def test_method_is_keyword(clf):
    r = clf.classify(ClassificationInput(title="Kaza haberi yaralı var"))
    assert r is not None
    assert r.method == "keyword"


def test_trafik_keyword_does_not_match_tem_substring(clf):
    r = clf.classify(
        ClassificationInput(
            title="Körfezli 3 küçük karateciye milli davet",
            summary="Sporcular ülkemizi temsil etmek üzere milli takıma seçildi.",
        )
    )
    assert r is None


def test_kulturel_keyword_does_not_match_anma_substring(clf):
    r = clf.classify(
        ClassificationInput(
            title="İzmit'te görev yapan öğretmenden kahreden haber!",
            summary="Yanmaz ailesini yasa boğan vefat haberi eğitim camiasını da üzdü.",
        )
    )
    assert r is None


def test_trafik_keyword_still_matches_tem_as_full_token(clf):
    r = clf.classify(
        ClassificationInput(title="TEM otoyolunda zincirleme kaza meydana geldi")
    )
    assert r is not None
    assert r.category == NewsCategory.TRAFIK_KAZASI
