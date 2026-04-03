import pytest

from app.services.classifier.keyword_classifier import KeywordClassifier
from app.services.classifier.schemas import ClassificationInput, NewsCategory


@pytest.fixture
def clf():
    return KeywordClassifier()


def test_yangin_keyword(clf):
    result = clf.classify(ClassificationInput(title="Gebze'de fabrika yangını çıktı"))
    assert result is not None
    assert result.category == NewsCategory.YANGIN
    assert result.confidence == 1.0
    assert "yangın" in result.matched_keywords


def test_trafik_keyword(clf):
    result = clf.classify(ClassificationInput(title="D100'de zincirleme trafik kazası"))
    assert result is not None
    assert result.category == NewsCategory.TRAFIK_KAZASI


def test_elektrik_keyword(clf):
    result = clf.classify(
        ClassificationInput(title="KKEDAŞ açıkladı: İzmit'te planlı kesinti")
    )
    assert result is not None
    assert result.category == NewsCategory.ELEKTRIK_KESINTISI


def test_hirsizlik_keyword(clf):
    result = clf.classify(ClassificationInput(title="Başiskele'de hırsız yakalandı"))
    assert result is not None
    assert result.category == NewsCategory.HIRSIZLIK


def test_kulturel_keyword(clf):
    result = clf.classify(ClassificationInput(title="İzmit'te yaz festivali başladı"))
    assert result is not None
    assert result.category == NewsCategory.KULTUREL_ETKINLIK


def test_unknown_returns_none(clf):
    result = clf.classify(ClassificationInput(title="Kocaeli'de yeni park açıldı"))
    assert result is None


def test_conflict_trafik_yangin_priority(clf):
    result = clf.classify(
        ClassificationInput(title="Trafik kazasında araç alev aldı yangın çıktı")
    )
    assert result is not None
    assert result.category == NewsCategory.TRAFIK_KAZASI


def test_matched_keywords_populated(clf):
    result = clf.classify(ClassificationInput(title="İtfaiye yangına müdahale etti"))
    assert result is not None
    assert len(result.matched_keywords) > 0


def test_method_is_keyword(clf):
    result = clf.classify(ClassificationInput(title="Kaza haberi yaralı var"))
    assert result is not None
    assert result.method == "keyword"


def test_trafik_keyword_does_not_match_tem_substring(clf):
    result = clf.classify(
        ClassificationInput(
            title="Körfezli 3 küçük karateciye milli davet",
            summary="Sporcular ülkemizi temsil etmek üzere milli takıma seçildi.",
        )
    )
    assert result is None


def test_kulturel_keyword_does_not_match_anma_substring(clf):
    result = clf.classify(
        ClassificationInput(
            title="İzmit'te görev yapan öğretmenden kahreden haber!",
            summary="Yas haberinin ardından eğitim camiası üzüldü.",
        )
    )
    assert result is None


def test_trafik_keyword_still_matches_tem_as_full_token(clf):
    result = clf.classify(
        ClassificationInput(title="TEM otoyolunda zincirleme kaza meydana geldi")
    )
    assert result is not None
    assert result.category == NewsCategory.TRAFIK_KAZASI


def test_hirsizlik_keyword_does_not_match_generic_yakalandi(clf):
    result = clf.classify(ClassificationInput(title="Şüpheli olay sonrası yakalandı"))
    assert result is None


def test_elektrik_keyword_does_not_match_generic_kesinti(clf):
    result = clf.classify(
        ClassificationInput(title="Program yayınında kısa süreli kesinti yaşandı")
    )
    assert result is None


def test_cultural_title_outweighs_crime_words_in_movie_roundup(clf):
    result = clf.classify(
        ClassificationInput(
            title="Sinema salonlarında 6 yeni film",
            content=(
                'Bu hafta sinema salonlarında 6 yeni film vizyona giriyor. '
                '"Soğuk Soygun" filmi ile iki beceriksiz hırsızın hikayesi anlatılıyor.'
            ),
        )
    )
    assert result is not None
    assert result.category == NewsCategory.KULTUREL_ETKINLIK
    assert result.all_scores["kulturel_etkinlik"] > result.all_scores["hirsizlik"]
