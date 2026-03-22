from app.services.ner.districts import (
    canonical_district_name,
    is_kocaeli_district,
    normalize_for_compare,
)


def test_normalize_for_compare_handles_turkish_characters():
    assert normalize_for_compare("Gölcük") == "golcuk"


def test_normalize_for_compare_handles_case_and_whitespace():
    assert normalize_for_compare("  İZMİT  ") == "izmit"


def test_is_kocaeli_district_returns_true_for_valid_district():
    assert is_kocaeli_district("Gebze") is True


def test_is_kocaeli_district_returns_false_for_invalid_city():
    assert is_kocaeli_district("İstanbul") is False


def test_canonical_district_name_returns_expected_value():
    assert canonical_district_name("basiskele") == "Başiskele"


def test_canonical_district_name_returns_none_for_unknown_value():
    assert canonical_district_name("Ankara") is None
