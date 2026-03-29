from app.services.ner.districts import recover_district_name

def test_recover_district_name_from_extended_span():
    assert recover_district_name("Gebze TEM") == "Gebze"
    assert recover_district_name("İzmit Sanayi Sitesi") == "İzmit"
    assert recover_district_name("Körfez D100") == "Körfez"

def test_recover_district_name_from_suffixless_form():
    assert recover_district_name("Derincede") == "Derince"
    assert recover_district_name("Başiskeledeki") == "Başiskele"


def test_hereke_maps_to_hereke():
    assert recover_district_name("Hereke sahilinde") == "Hereke"


def test_single_letter_suffixes_do_not_match():
    assert recover_district_name("Gebzei") is None
