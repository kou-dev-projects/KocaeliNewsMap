from app.domain.enums import NewsCategory
from app.services.classifier.schemas import ClassificationResult
from app.services.logical_location import build_logical_location_candidates
from app.services.ner.schemas import LocationCandidate, NERResult


def _classification(category: NewsCategory) -> ClassificationResult:
    return ClassificationResult(
        category=category,
        confidence=0.9,
        method="test",
    )


def test_builds_highway_candidate_from_road_and_neighborhood():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[
            LocationCandidate(
                original_text="Yahya Kaptan Mahallesi",
                normalized_text="yahya kaptan mahallesi",
                score=0.9,
                is_kocaeli_district=False,
                district="Izmit",
                neighborhood="Yahya Kaptan Mahallesi",
            )
        ],
        validated_districts=["Izmit"],
        provider="stub",
    )

    candidates = build_logical_location_candidates(
        title="TEM otoyolunda kaza meydana geldi",
        summary=None,
        body="Yahya Kaptan Mahallesi gecisinde trafik kilitlendi.",
        classification=_classification(NewsCategory.TRAFIK_KAZASI),
        ner_result=ner_result,
        fallback_district="izmit",
    )

    assert candidates[0].strategy == "logic_highway_segment"
    assert candidates[0].address == "Anadolu Otoyolu, Yahya Kaptan Mahallesi"
    assert candidates[0].district_hint == "Izmit"


def test_builds_cinema_candidate_for_movie_roundup():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[],
        validated_districts=[],
        provider="stub",
    )

    candidates = build_logical_location_candidates(
        title="Sinema salonlarinda 6 yeni film",
        summary=None,
        body="Bu hafta sinema salonlarinda yeni filmler vizyona giriyor.",
        classification=_classification(NewsCategory.KULTUREL_ETKINLIK),
        ner_result=ner_result,
        fallback_district=None,
    )

    cinema_candidate = next(
        candidate
        for candidate in candidates
        if candidate.strategy == "logic_cinema_release"
    )

    assert cinema_candidate.address == "Paribu Cineverse 41 Burda AVM"
    assert cinema_candidate.geocode_status == "approximate"


def test_score_story_without_explicit_venue_does_not_invent_stadium():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[],
        validated_districts=[],
        provider="stub",
    )

    candidates = build_logical_location_candidates(
        title="Kocaelispor 2-1 kazandi",
        summary="Mac sonucu taraftari sevindirdi.",
        body="Kocaelispor rakibini 2-1 maglup etti.",
        classification=_classification(NewsCategory.KULTUREL_ETKINLIK),
        ner_result=ner_result,
        fallback_district=None,
    )

    assert all("stadium" not in candidate.strategy for candidate in candidates)


def test_named_stadium_uses_catalog_display_name():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[],
        validated_districts=[],
        provider="stub",
    )

    candidates = build_logical_location_candidates(
        title="Darica Ilce Stadyumu'nda mac sonucu belli oldu",
        summary="Canli skor takibi yapan taraftarlar galibiyeti kutladi.",
        body="Darica Ilce Stadyumu'nda karsilasma oynandi.",
        classification=_classification(NewsCategory.KULTUREL_ETKINLIK),
        ner_result=ner_result,
        fallback_district=None,
    )

    sports_candidate = next(
        candidate
        for candidate in candidates
        if candidate.strategy == "logic_stadium_mentioned"
    )

    assert sports_candidate.address == "Darıca İlçe Stadyumu"


def test_non_sports_story_does_not_match_gol_inside_district_name():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[],
        validated_districts=["Izmit"],
        provider="stub",
    )

    candidates = build_logical_location_candidates(
        title="Muhtarlar, Turkiye'de ilk olan bu mekandan memnun",
        summary=None,
        body="Gebze, Dilovasi, Cayirova, Golcuk, Kartepe ve Kandira gibi ilcelerden gelen muhtarlar icin merkez acildi.",
        classification=_classification(NewsCategory.KULTUREL_ETKINLIK),
        ner_result=ner_result,
        fallback_district="izmit",
    )

    assert all(
        not candidate.strategy.startswith("logic_") or "stadium" not in candidate.strategy
        for candidate in candidates
    )


def test_team_name_without_match_context_does_not_build_stadium_fallback():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[],
        validated_districts=[],
        provider="stub",
    )

    candidates = build_logical_location_candidates(
        title="Kocaelispor'dan taraftara ozel kart projesi",
        summary="Kulubun banka is birligi icin gorusmelerde sona geldigi ogrenildi.",
        body=(
            "Kocaelispor, gelir kaynaklarini cesitlendirmek ve marka degerini "
            "artirmak amaciyla yeni bir kart projesi hazirliyor."
        ),
        classification=_classification(NewsCategory.UNKNOWN),
        ner_result=ner_result,
        fallback_district=None,
    )

    assert all("stadium" not in candidate.strategy for candidate in candidates)


def test_non_traffic_story_with_d100_does_not_build_highway_candidate():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[
            LocationCandidate(
                original_text="D-100 Karayolu",
                normalized_text="d 100 karayolu",
                score=0.88,
                is_kocaeli_district=False,
                district="Izmit",
            )
        ],
        validated_districts=["Izmit"],
        provider="stub",
    )

    candidates = build_logical_location_candidates(
        title="Cezaevinde tanistigi adama 3 milyon TL kaptirdi",
        summary=None,
        body="Sahis, D-100 Karayolu uzerinde basin aciklamasi yapti.",
        classification=_classification(NewsCategory.HIRSIZLIK),
        ner_result=ner_result,
        fallback_district="izmit",
    )

    assert all(candidate.strategy != "logic_highway_segment" for candidate in candidates)


def test_transport_guide_prefers_named_stadium_over_neighborhood_noise():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[
            LocationCandidate(
                original_text="Yeni Mahalle Mahallesi",
                normalized_text="Yeni Mahalle Mahallesi",
                score=0.91,
                is_kocaeli_district=False,
                district="Golcuk",
                neighborhood="Yeni Mahalle Mahallesi",
            ),
            LocationCandidate(
                original_text="Kocaeli Stadyumu'na",
                normalized_text="Kocaeli Stadyumu",
                score=0.89,
                is_kocaeli_district=False,
                district="Izmit",
            ),
        ],
        validated_districts=["Golcuk", "Izmit"],
        provider="stub",
    )

    candidates = build_logical_location_candidates(
        title="Kocaelispor - Basaksehir maci ulasim rehberi aciklandi",
        summary=None,
        body=(
            "Mac gunu ulasim ozeti: UlasimPark, Kurucesme - Stadyum hattinda "
            "tramvaylar ve ozel otobus seferleri planladi."
        ),
        classification=_classification(NewsCategory.UNKNOWN),
        ner_result=ner_result,
        fallback_district="golcuk",
    )

    assert all(candidate.strategy != "logic_highway_segment" for candidate in candidates)
    stadium_candidate = next(
        candidate
        for candidate in candidates
        if candidate.strategy == "logic_stadium_mentioned"
    )
    assert stadium_candidate.address == "Kocaeli Stadyumu"
