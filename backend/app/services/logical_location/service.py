from __future__ import annotations

import re
from typing import Optional

from app.domain.enums import NewsCategory, normalize_kocaeli_district
from app.services.classifier.schemas import ClassificationResult
from app.services.ner.districts import normalize_for_compare
from app.services.ner.schemas import NERResult

from .catalog import LogicalCatalogEntry, build_logical_location_catalog
from .schemas import LogicalLocationCandidate

_ROAD_ALIASES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("tem otoyolu", "tem yolu", "anadolu otoyolu", "o-4", "o4"), "Anadolu Otoyolu"),
    (("d-100", "d100", "e-5", "e5", "d 100", "karayolu"), "D-100 Karayolu"),
    (("kuzey marmara otoyolu",), "Kuzey Marmara Otoyolu"),
    (("salim dervisoglu caddesi",), "Salim Dervisoglu Caddesi"),
)

_CINEMA_KEYWORDS = (
    "sinema",
    "vizyon",
    "vizyona",
    "seans",
    "beyaz perde",
    "film haftasi",
    "yeni film",
    "film vizyona",
    "sinema salon",
)

_SPORTS_KEYWORDS = (
    "canli skor",
    "mac sonucu",
    "macta",
    "karsilasma",
    "rakibini",
    "skor",
    "puan durumu",
    "galibiyet",
    "berabere",
    "penalti",
    "ilk yari",
    "ikinci yari",
    "stadyum",
    "stad",
)

_TRANSPORT_GUIDE_KEYWORDS = (
    "ulasim rehberi",
    "ulasim plani",
    "mac gunu ulasim",
    "stadyuma nasil gidilir",
    "nasil gidilir",
    "otobus seferleri",
    "ek tramvay",
    "tramvaylar",
    "taraftar tasimak",
    "taraftar tasimasi",
    "ozel otobus seferleri",
    "ring seferi",
    "ulasimpark",
)

_SPORTS_VENUE_INTENT_KEYWORDS = (
    "stadyuma",
    "stadyum",
    "stadi",
    "arena",
    "tribun",
    "ulasim",
    "sefer",
    "tramvay",
    "otobus",
)

_SCORE_PATTERN = re.compile(r"\b\d{1,2}\s*-\s*\d{1,2}\b")
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_SPORTS_TOKENS = frozenset(
    {
        "mac",
        "macta",
        "skor",
        "gol",
        "lig",
        "puan",
        "stadyum",
        "stad",
        "arena",
        "futbol",
        "basketbol",
        "voleybol",
    }
)

_PRECISION_HINTS = (
    "mahallesi",
    "mahalle",
    "sokak",
    "cadde",
    "bulvar",
    "baraji",
    "goleti",
    "tesisi",
    "stadyumu",
    "stadi",
    "arena",
    "kampusu",
    "terminali",
    "otoyolu",
)

_LOGICAL_CATALOG = build_logical_location_catalog()


def build_logical_location_candidates(
    *,
    title: str,
    summary: Optional[str],
    body: str,
    classification: ClassificationResult,
    ner_result: NERResult,
    fallback_district: Optional[str],
) -> list[LogicalLocationCandidate]:
    text = " ".join(
        part.strip()
        for part in (title, summary or "", body or "")
        if part and part.strip()
    )
    normalized_text = normalize_for_compare(text)
    district = _select_district(ner_result, fallback_district)
    neighborhood = _select_neighborhood(ner_result)

    candidates: list[LogicalLocationCandidate] = []
    seen: set[tuple[str, str | None, str]] = set()

    def add(candidate: LogicalLocationCandidate) -> None:
        key = (
            normalize_for_compare(candidate.address),
            normalize_for_compare(candidate.district_hint)
            if candidate.district_hint
            else None,
            candidate.strategy,
        )
        if key in seen:
            return
        seen.add(key)
        candidates.append(candidate)

    road_name = _extract_road_name(normalized_text)
    if road_name and (neighborhood or district) and _should_build_highway_candidate(
        normalized_text=normalized_text,
        classification=classification,
    ):
        address_parts = [road_name]
        if neighborhood:
            address_parts.append(neighborhood)
        add(
            LogicalLocationCandidate(
                address=", ".join(address_parts),
                district_hint=district,
                neighborhood=neighborhood,
                location_text=(
                    road_name if not neighborhood else f"{road_name}, {neighborhood}"
                ),
                strategy="logic_highway_segment",
                geocode_status="approximate",
            )
        )

    if _is_cinema_story(
        normalized_text,
        classification.category,
    ) and not _has_precise_place_candidate(ner_result):
        venue = _select_cinema_venue(district)
        add(
            LogicalLocationCandidate(
                address=venue.canonical_name,
                district_hint=venue.district,
                location_text=venue.canonical_name,
                strategy="logic_cinema_release",
                geocode_status="approximate",
            )
        )

    sports_candidate = _select_sports_candidate(
        normalized_text=normalized_text,
        district=district,
        ner_result=ner_result,
    )
    if sports_candidate is not None:
        add(sports_candidate)

    return candidates


def _extract_road_name(normalized_text: str) -> str | None:
    for aliases, display_name in _ROAD_ALIASES:
        if any(alias in normalized_text for alias in aliases):
            return display_name
    for road in _LOGICAL_CATALOG.roads:
        if any(alias in normalized_text for alias in road.normalized_aliases):
            return road.canonical_name
    return None


def _is_cinema_story(normalized_text: str, category: NewsCategory) -> bool:
    if category != NewsCategory.KULTUREL_ETKINLIK:
        return False
    return any(keyword in normalized_text for keyword in _CINEMA_KEYWORDS)


def _has_precise_place_candidate(ner_result: NERResult) -> bool:
    for candidate in ner_result.location_candidates:
        normalized = normalize_for_compare(candidate.original_text)
        if candidate.neighborhood:
            return True
        if any(hint in normalized for hint in _PRECISION_HINTS):
            return True
    return False


def _select_cinema_venue(district: str | None) -> LogicalCatalogEntry:
    if district:
        normalized = normalize_for_compare(district)
        venue = _LOGICAL_CATALOG.cinemas_by_district.get(normalized)
        if venue is not None:
            return venue
    return _LOGICAL_CATALOG.default_cinema


def _select_sports_candidate(
    *,
    normalized_text: str,
    district: str | None,
    ner_result: NERResult,
) -> LogicalLocationCandidate | None:
    if not _is_sports_story(normalized_text):
        return None

    mentioned_stadium = _match_named_venue(
        normalized_text,
        _LOGICAL_CATALOG.stadiums,
    ) or _match_named_venue_candidates(ner_result, _LOGICAL_CATALOG.stadiums)
    if mentioned_stadium is not None:
        return LogicalLocationCandidate(
            address=mentioned_stadium.canonical_name,
            district_hint=mentioned_stadium.district,
            location_text=mentioned_stadium.canonical_name,
            strategy="logic_stadium_mentioned",
            geocode_status="resolved",
        )

    if _has_stadium_candidate(ner_result):
        return None

    if not _is_sports_venue_story(normalized_text):
        return None

    team_home_venue = _match_named_venue(
        normalized_text,
        _LOGICAL_CATALOG.team_home_venues,
    )
    if team_home_venue is not None:
        return LogicalLocationCandidate(
            address=team_home_venue.canonical_name,
            district_hint=team_home_venue.district,
            location_text=team_home_venue.canonical_name,
            strategy="logic_team_home_stadium",
            geocode_status="approximate",
        )

    district_stadium = _select_district_stadium(district)
    if district_stadium is None:
        return None

    return LogicalLocationCandidate(
        address=district_stadium.canonical_name,
        district_hint=district_stadium.district,
        location_text=district_stadium.canonical_name,
        strategy="logic_district_stadium",
        geocode_status="approximate",
    )


def _is_sports_story(normalized_text: str) -> bool:
    tokens = set(_TOKEN_PATTERN.findall(normalized_text))
    has_team_alias = (
        _match_named_venue(normalized_text, _LOGICAL_CATALOG.team_home_venues)
        is not None
    )
    has_score = _SCORE_PATTERN.search(normalized_text) is not None
    has_sports_phrase = any(keyword in normalized_text for keyword in _SPORTS_KEYWORDS)
    has_sports_token = any(token in tokens for token in _SPORTS_TOKENS)

    if has_score or has_sports_phrase:
        return True

    if not has_team_alias:
        return False

    # Team names alone are too noisy for location fallback. Require clear match context.
    return has_sports_token


def _is_transport_guide_story(normalized_text: str) -> bool:
    return any(keyword in normalized_text for keyword in _TRANSPORT_GUIDE_KEYWORDS)


def _is_sports_venue_story(normalized_text: str) -> bool:
    has_team_alias = (
        _match_named_venue(normalized_text, _LOGICAL_CATALOG.team_home_venues)
        is not None
    )
    has_venue_intent = any(
        keyword in normalized_text for keyword in _SPORTS_VENUE_INTENT_KEYWORDS
    )
    return has_team_alias and has_venue_intent


def _should_build_highway_candidate(
    *,
    normalized_text: str,
    classification: ClassificationResult,
) -> bool:
    if classification.category != NewsCategory.TRAFIK_KAZASI:
        return False

    if _is_transport_guide_story(normalized_text):
        return False

    return True


def _has_stadium_candidate(ner_result: NERResult) -> bool:
    for candidate in ner_result.location_candidates:
        normalized = normalize_for_compare(candidate.original_text)
        if "stadyum" in normalized or "stadi" in normalized or "arena" in normalized:
            return True
    return False


def _match_named_venue(
    normalized_text: str,
    lookup: tuple[LogicalCatalogEntry, ...]
    | tuple[tuple[tuple[str, ...], LogicalCatalogEntry], ...],
) -> LogicalCatalogEntry | None:
    for item in lookup:
        if isinstance(item, tuple):
            aliases, venue = item
            if any(alias in normalized_text for alias in aliases):
                return venue
            continue

        if any(alias in normalized_text for alias in item.normalized_aliases):
            return item
    return None


def _match_named_venue_candidates(
    ner_result: NERResult,
    lookup: tuple[LogicalCatalogEntry, ...]
    | tuple[tuple[tuple[str, ...], LogicalCatalogEntry], ...],
) -> LogicalCatalogEntry | None:
    for candidate in ner_result.location_candidates:
        candidate_text = normalize_for_compare(
            " ".join(
                part
                for part in (
                    candidate.original_text or "",
                    candidate.normalized_text or "",
                )
                if part
            )
        )
        if not candidate_text:
            continue

        venue = _match_named_venue(candidate_text, lookup)
        if venue is not None:
            return venue

    return None


def _select_district_stadium(district: str | None) -> LogicalCatalogEntry | None:
    if district is None:
        return None

    normalized_district = normalize_for_compare(district)
    for venue in _LOGICAL_CATALOG.stadiums:
        if normalize_for_compare(venue.district or "") == normalized_district:
            return venue

    return None


def _select_district(
    ner_result: NERResult,
    fallback_district: Optional[str],
) -> str | None:
    if fallback_district:
        district_enum = normalize_kocaeli_district(fallback_district)
        if district_enum:
            return _district_display_name(district_enum.value)

    for candidate in ner_result.location_candidates:
        if candidate.district:
            district_enum = normalize_kocaeli_district(candidate.district)
            if district_enum:
                return _district_display_name(district_enum.value)

    for district in ner_result.validated_districts:
        district_enum = normalize_kocaeli_district(district)
        if district_enum:
            return _district_display_name(district_enum.value)

    return None


def _select_neighborhood(ner_result: NERResult) -> str | None:
    for candidate in ner_result.location_candidates:
        if candidate.neighborhood:
            return candidate.neighborhood.strip()
    return None


def _district_display_name(value: str) -> str | None:
    district_enum = normalize_kocaeli_district(value)
    if district_enum is None:
        return None
    return district_enum.value[:1].upper() + district_enum.value[1:]
