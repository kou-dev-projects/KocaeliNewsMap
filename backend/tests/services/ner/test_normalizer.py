from app.services.ner.normalizer import normalize_location_text


def test_removes_locative_suffix():
    assert normalize_location_text("İzmit'te") == "İzmit"


def test_removes_ablative_suffix():
    assert normalize_location_text("Gebze'den") == "Gebze"


def test_removes_dative_suffix():
    assert normalize_location_text("Darıca'ya") == "Darıca"


def test_removes_genitive_suffix():
    assert normalize_location_text("Kocaeli'nin") == "Kocaeli"


def test_empty_string():
    assert normalize_location_text("") == ""


def test_no_suffix():
    assert normalize_location_text("İzmit") == "İzmit"


def test_removes_trailing_punctuation():
    assert normalize_location_text("Gebze,") == "Gebze"