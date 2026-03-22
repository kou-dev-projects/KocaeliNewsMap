from app.services.ner.normalizer import normalize_location_text


def test_removes_locative_suffix():
    assert normalize_location_text("İzmit'te") == "İzmit"


def test_removes_ablative_suffix():
    assert normalize_location_text("Gebze'den") == "Gebze"


def test_removes_dative_suffix():
    assert normalize_location_text("Başiskele'ye") == "Başiskele"


def test_removes_genitive_suffix():
    assert normalize_location_text("Kartepe'nin") == "Kartepe"


def test_preserves_plain_location():
    assert normalize_location_text("Derince") == "Derince"


def test_returns_empty_for_blank_input():
    assert normalize_location_text("   ") == ""
