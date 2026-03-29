from app.domain.enums import (
    NewsCategory,
    KocaeliDistrict,
    normalize_kocaeli_district,
    normalize_news_category,
)


def test_normalize_news_category_accepts_slug_and_display_forms():
    assert normalize_news_category("trafik_kazasi") == NewsCategory.TRAFIK_KAZASI
    assert normalize_news_category("Trafik Kazası") == NewsCategory.TRAFIK_KAZASI
    assert normalize_news_category("Kültürel Etkinlikler") == NewsCategory.KULTUREL_ETKINLIK


def test_normalize_kocaeli_district_accepts_multiple_spellings():
    assert normalize_kocaeli_district("izmit") == KocaeliDistrict.IZMIT
    assert normalize_kocaeli_district("Izmit") == KocaeliDistrict.IZMIT
    assert normalize_kocaeli_district("İzmit") == KocaeliDistrict.IZMIT
    assert normalize_kocaeli_district("Hereke") == KocaeliDistrict.HEREKE
