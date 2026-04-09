from dataclasses import dataclass
from functools import lru_cache

from app.services.ner.districts import normalize_for_compare
from app.services.ner.gazetteer_catalog import GazetteerEntry, build_entries


@dataclass(frozen=True)
class LogicalCatalogEntry:
    canonical_name: str
    district: str | None
    feature_type: str
    source_key: str
    normalized_aliases: tuple[str, ...]


@dataclass(frozen=True)
class LogicalLocationCatalog:
    roads: tuple[LogicalCatalogEntry, ...]
    stadiums: tuple[LogicalCatalogEntry, ...]
    cinemas: tuple[LogicalCatalogEntry, ...]
    default_cinema: LogicalCatalogEntry
    cinemas_by_district: dict[str, LogicalCatalogEntry]
    team_home_venues: tuple[tuple[tuple[str, ...], LogicalCatalogEntry], ...]


_DEFAULT_CINEMA_CANONICAL = "Paribu Cineverse 41 Burda AVM"

_DISTRICT_CINEMA_CANONICALS: dict[str, str] = {
    "izmit": "Paribu Cineverse 41 Burda AVM",
    "basiskele": "Symbol Kocaeli AVM Sinemalari",
    "kartepe": "Paribu Cineverse 41 Burda AVM",
    "derince": "Paribu Cineverse 41 Burda AVM",
    "korfez": "Paribu Cineverse 41 Burda AVM",
    "golcuk": "Symbol Kocaeli AVM Sinemalari",
    "karamursel": "Symbol Kocaeli AVM Sinemalari",
    "gebze": "Paribu Cineverse Gebze Center AVM",
    "darica": "Paribu Cineverse Gebze Center AVM",
    "cayirova": "Paribu Cineverse Gebze Center AVM",
    "dilovasi": "Paribu Cineverse Gebze Center AVM",
}

_TEAM_HOME_CANONICALS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("kocaelispor",), "Kocaeli Stadyumu"),
    (("gebzespor",), "Gebze Alaettin Kurt Stadyumu"),
    (("darica genclerbirligi", "darica gb"), "Darica Ilce Stadyumu"),
    (("karamurselspor",), "Karamursel Ilce Stadi"),
)


def _normalize_aliases(entry: GazetteerEntry) -> tuple[str, ...]:
    aliases = {
        normalize_for_compare(alias)
        for alias in (entry.canonical_name, *entry.aliases)
        if normalize_for_compare(alias)
    }
    return tuple(sorted(aliases))


def _to_logical_entry(entry: GazetteerEntry) -> LogicalCatalogEntry:
    return LogicalCatalogEntry(
        canonical_name=entry.canonical_name,
        district=entry.district,
        feature_type=entry.feature_type,
        source_key=entry.source_key,
        normalized_aliases=_normalize_aliases(entry),
    )


def _resolve_entry(
    entry_map: dict[str, GazetteerEntry],
    canonical_name: str,
) -> LogicalCatalogEntry:
    normalized = normalize_for_compare(canonical_name)
    entry = entry_map.get(normalized)
    if entry is None:
        raise KeyError(f"Gazetteer entry missing for logical catalog: {canonical_name}")
    return _to_logical_entry(entry)


@lru_cache(maxsize=1)
def build_logical_location_catalog() -> LogicalLocationCatalog:
    entries = build_entries()
    entry_map = {
        normalize_for_compare(entry.canonical_name): entry
        for entry in entries
    }

    roads = tuple(
        _to_logical_entry(entry)
        for entry in entries
        if entry.feature_type == "road"
    )
    stadiums = tuple(
        _to_logical_entry(entry)
        for entry in entries
        if entry.feature_type == "stadium"
    )
    cinemas = tuple(
        _to_logical_entry(entry)
        for entry in entries
        if entry.feature_type == "cinema"
    )

    default_cinema = _resolve_entry(entry_map, _DEFAULT_CINEMA_CANONICAL)
    cinemas_by_district = {
        district: _resolve_entry(entry_map, canonical_name)
        for district, canonical_name in _DISTRICT_CINEMA_CANONICALS.items()
    }
    team_home_venues = tuple(
        (
            tuple(normalize_for_compare(alias) for alias in aliases),
            _resolve_entry(entry_map, canonical_name),
        )
        for aliases, canonical_name in _TEAM_HOME_CANONICALS
    )

    return LogicalLocationCatalog(
        roads=roads,
        stadiums=stadiums,
        cinemas=cinemas,
        default_cinema=default_cinema,
        cinemas_by_district=cinemas_by_district,
        team_home_venues=team_home_venues,
    )
