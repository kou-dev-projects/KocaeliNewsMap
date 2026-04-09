from app.services.ner.morphology import strip_suffixes, generate_candidates


def test_strip_apostrophe_locative():
    assert strip_suffixes("Çayırova'daki") == "Çayırova"


def test_strip_apostrophe_ablative():
    assert strip_suffixes("İzmit'ten") == "İzmit"


def test_strip_no_suffix():
    assert strip_suffixes("Gebze") == "Gebze"


def test_generate_candidates_includes_original():
    candidates = generate_candidates("Çayırova'daki")
    assert "Çayırova'daki" in candidates


def test_generate_candidates_includes_stripped():
    candidates = generate_candidates("Çayırova'daki")
    assert "Çayırova" in candidates


def test_strip_suffix_without_apostrophe():
    result = strip_suffixes("Izmitte")
    # Kural tabanlı — "te" suffix'i kaldırır
    assert result == "Izmit"


def test_strip_suffix_preserves_lexical_ending_si():
    assert strip_suffixes("Caddesi") == "Caddesi"