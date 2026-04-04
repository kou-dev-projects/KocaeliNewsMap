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


def test_hirsizlik_keyword_matches_dolandiricilik(clf):
    result = clf.classify(
        ClassificationInput(
            title="Verdiği paranın 2 katını alacağı vaadiyle 3 milyon TL dolandırıldı"
        )
    )
    assert result is not None
    assert result.category == NewsCategory.HIRSIZLIK


def test_hirsizlik_keyword_matches_suc_unsurlari(clf):
    result = clf.classify(
        ClassificationInput(title="Üst aramasıyla başladı, evinden suç unsurları çıktı")
    )
    assert result is not None
    assert result.category == NewsCategory.HIRSIZLIK


def test_electrocution_story_is_not_classified_as_fire_or_outage(clf):
    result = clf.classify(
        ClassificationInput(
            title="Elektrik akımına kapılan yaşlı adam hayatını kaybetti",
            content=(
                "Olay, köprü onarımı sırasında meydana geldi. Direğin kablosunu "
                "kesmek isteyen kişi elektrik akımına kapıldı ve tüm müdahalelere "
                "rağmen kurtarılamadı."
            ),
        )
    )
    assert result is None


def test_kulturel_keyword(clf):
    result = clf.classify(ClassificationInput(title="İzmit'te yaz festivali başladı"))
    assert result is not None
    assert result.category == NewsCategory.KULTUREL_ETKINLIK


def test_kulturel_keyword_matches_library_week(clf):
    result = clf.classify(
        ClassificationInput(title="Kütüphane Haftası kapsamında söyleşi düzenlendi")
    )
    assert result is not None
    assert result.category == NewsCategory.KULTUREL_ETKINLIK


def test_kulturel_keyword_matches_student_meeting(clf):
    result = clf.classify(
        ClassificationInput(title="Polis öğrenci buluşması unutulmaz anlar yaşattı")
    )
    assert result is not None
    assert result.category == NewsCategory.KULTUREL_ETKINLIK


def test_kulturel_keyword_matches_awareness_day(clf):
    result = clf.classify(
        ClassificationInput(title="Kandıra'da Otizm Farkındalık Günü'ne anlamlı etkinlik")
    )
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
                "Bu hafta sinema salonlarında 6 yeni film vizyona giriyor. "
                '"Soğuk Soygun" filmi ile iki beceriksiz hırsızın hikayesi anlatılıyor.'
            ),
        )
    )
    assert result is not None
    assert result.category == NewsCategory.KULTUREL_ETKINLIK
    assert result.all_scores["kulturel_etkinlik"] > result.all_scores["hirsizlik"]
