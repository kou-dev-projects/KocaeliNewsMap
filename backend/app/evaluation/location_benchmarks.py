from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.enums import NewsCategory


DISTRICT_GROUP_EXPECTATIONS: dict[str, list[str]] = {
    "duplicate_of_grp_01": ["Gebze"],
    "duplicate_of_grp_02": ["Izmit"],
    "duplicate_of_grp_03": ["Darica"],
    "duplicate_of_grp_04": ["Golcuk"],
    "duplicate_of_grp_05": [],
    "duplicate_of_grp_06": ["Korfez"],
    "duplicate_of_grp_07": ["Basiskele"],
    "duplicate_of_grp_08": ["Kartepe"],
    "duplicate_of_grp_09": ["Derince"],
    "duplicate_of_grp_10": ["Gebze"],
    "duplicate_of_grp_11": ["Kandira"],
    "duplicate_of_grp_12": ["Cayirova"],
    "duplicate_of_grp_13": ["Izmit"],
    "duplicate_of_grp_14": ["Kartepe"],
    "duplicate_of_grp_15": ["Darica"],
    "duplicate_of_grp_16": ["Dilovasi"],
    "duplicate_of_grp_17": ["Derince"],
    "duplicate_of_grp_18": ["Hereke"],
    "duplicate_of_grp_19": ["Basiskele"],
    "duplicate_of_grp_20": ["Golcuk"],
    "duplicate_of_grp_21": ["Izmit"],
    "duplicate_of_grp_22": ["Kandira"],
    "duplicate_of_grp_23": ["Cayirova"],
    "duplicate_of_grp_24": ["Gebze"],
    "duplicate_of_grp_25": ["Basiskele"],
}


@dataclass(frozen=True)
class SeedCandidateSpec:
    original_text: str
    district: str | None = None
    neighborhood: str | None = None
    is_kocaeli_district: bool = False
    feature_type: str | None = None
    score: float = 0.9


@dataclass(frozen=True)
class LogicalBenchmarkCase:
    name: str
    title: str
    body: str
    category: NewsCategory
    expected_strategy: str | None
    expected_address: str | None
    fallback_district: str | None = None
    summary: str | None = None
    validated_districts: list[str] = field(default_factory=list)
    seed_candidates: list[SeedCandidateSpec] = field(default_factory=list)


LOGICAL_BENCHMARK_CASES: tuple[LogicalBenchmarkCase, ...] = (
    LogicalBenchmarkCase(
        name="highway_with_neighborhood",
        title="TEM otoyolunda kaza meydana geldi",
        body="Yahya Kaptan Mahallesi gecisinde trafik kilitlendi.",
        category=NewsCategory.TRAFIK_KAZASI,
        fallback_district="Izmit",
        validated_districts=["Izmit"],
        seed_candidates=[
            SeedCandidateSpec(
                original_text="Yahya Kaptan Mahallesi",
                district="Izmit",
                neighborhood="Yahya Kaptan Mahallesi",
                feature_type="neighborhood",
            )
        ],
        expected_strategy="logic_highway_segment",
        expected_address="Anadolu Otoyolu, Yahya Kaptan Mahallesi",
    ),
    LogicalBenchmarkCase(
        name="highway_with_district_only",
        title="Korfez D-100 gecisinde kaza oldu",
        body="Yagis nedeniyle ulasim bir sure kontrollu saglandi.",
        category=NewsCategory.TRAFIK_KAZASI,
        fallback_district="Korfez",
        validated_districts=["Korfez"],
        expected_strategy="logic_highway_segment",
        expected_address="D-100 Karayolu",
    ),
    LogicalBenchmarkCase(
        name="cinema_roundup_default",
        title="Sinema salonlarinda 6 yeni film",
        body="Bu hafta sinema salonlarinda yeni filmler vizyona giriyor.",
        category=NewsCategory.KULTUREL_ETKINLIK,
        expected_strategy="logic_cinema_release",
        expected_address="Paribu Cineverse 41 Burda AVM",
    ),
    LogicalBenchmarkCase(
        name="cinema_roundup_gebze",
        title="Gebze'de vizyon haftasi basladi",
        body="Sinema salonlarinda yeni filmler vizyona girdi.",
        category=NewsCategory.KULTUREL_ETKINLIK,
        fallback_district="Gebze",
        validated_districts=["Gebze"],
        expected_strategy="logic_cinema_release",
        expected_address="Paribu Cineverse Gebze Center AVM",
    ),
    LogicalBenchmarkCase(
        name="team_home_stadium",
        title="Kocaelispor 2-1 kazandi",
        body="Mac sonucu taraftari sevindirdi.",
        category=NewsCategory.KULTUREL_ETKINLIK,
        expected_strategy="logic_team_home_stadium",
        expected_address="Kocaeli Stadyumu",
    ),
    LogicalBenchmarkCase(
        name="mentioned_stadium",
        title="Darica Ilce Stadyumu'nda mac sonucu belli oldu",
        body="Canli skor takibi yapan taraftarlar galibiyeti kutladi.",
        category=NewsCategory.KULTUREL_ETKINLIK,
        expected_strategy="logic_stadium_mentioned",
        expected_address="Darıca İlçe Stadyumu",
    ),
    LogicalBenchmarkCase(
        name="district_stadium_fallback",
        title="Gebze 1-0 galip geldi",
        body="Mac sonucu sonrasinda taraftarlar sevince boguldu.",
        category=NewsCategory.KULTUREL_ETKINLIK,
        fallback_district="Gebze",
        validated_districts=["Gebze"],
        expected_strategy="logic_district_stadium",
        expected_address="Gebze Ilce Stadyumu",
    ),
    LogicalBenchmarkCase(
        name="no_sports_false_positive",
        title="Muhtarlar, Turkiye'de ilk olan bu mekandan memnun",
        body="Gebze, Dilovasi, Cayirova, Golcuk, Kartepe ve Kandira gibi ilcelerden gelen muhtarlar icin merkez acildi.",
        category=NewsCategory.KULTUREL_ETKINLIK,
        fallback_district="Izmit",
        validated_districts=["Izmit"],
        expected_strategy=None,
        expected_address=None,
    ),
)
