from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.db.database import db
from app.domain.enums import normalize_kocaeli_district, normalize_news_category
from app.services.dataset_generation import resolve_visible_generation_query
from app.utils.content_cleaning import clean_news_text
from app.schemas import (
    NewsDashboardResponse,
    NewsListItem,
    NewsListResponse,
    NewsMapItem,
    NewsMapResponse,
    NewsResponse,
    NewsStatsResponse,
    StatsBucket,
)

router = APIRouter(prefix="/news", tags=["news"])
_ACTIVE_RECORD_QUERY: dict[str, Any] = {"record_status": {"$ne": "merged_duplicate"}}

_VALID_GEO_POINT_QUERY: dict[str, Any] = {
    "geocode_point.type": "Point",
    "geocode_point.coordinates.0": {"$type": "number"},
    "geocode_point.coordinates.1": {"$type": "number"},
}

_NEWS_LIST_PROJECTION = {
    "title": 1,
    "summary": 1,
    "source_name_snapshot": 1,
    "source_url_snapshot": 1,
    "canonical_url": 1,
    "published_at": 1,
    "category_predicted": 1,
    "category_confidence": 1,
    "district_predicted": 1,
    "district_confidence": 1,
    "geocode_status": 1,
    "geocode_point": 1,
    "kaynak_listesi": 1,
    "created_at": 1,
}

_NEWS_MAP_PROJECTION = {
    "title": 1,
    "summary": 1,
    "source_name_snapshot": 1,
    "source_url_snapshot": 1,
    "canonical_url": 1,
    "published_at": 1,
    "category_predicted": 1,
    "category_confidence": 1,
    "district_predicted": 1,
    "geocode_status": 1,
    "geocode_point": 1,
}


def _normalize_query_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_multi_values(values: Optional[list[str]]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for value in values or []:
        for part in value.split(","):
            clean = part.strip()
            if not clean:
                continue
            lowered = clean.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(clean)

    return normalized


def _merge_query(query: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(query)

    for key, value in extra.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = {**merged[key], **value}
            continue
        merged[key] = value

    return merged


def _stats_facet_pipeline(
    query: dict[str, Any],
    *,
    last_3d_cutoff: datetime,
) -> list[dict[str, Any]]:
    return [
        {"$match": query},
        {
            "$facet": {
                "meta": _stats_meta_pipeline(last_3d_cutoff=last_3d_cutoff),
                "categories": _bucket_pipeline("category_predicted"),
                "districts": _bucket_pipeline("district_predicted"),
                "geocoded": _geocoded_total_pipeline(),
            }
        },
    ]


def _stats_meta_pipeline(*, last_3d_cutoff: datetime) -> list[dict[str, Any]]:
    return [
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "active_sources": {"$addToSet": "$source_id"},
                "last_3d_total": {
                    "$sum": {
                        "$cond": [
                            {"$gte": ["$published_at", last_3d_cutoff]},
                            1,
                            0,
                        ]
                    }
                },
            }
        }
    ]


def _bucket_pipeline(field: str) -> list[dict[str, Any]]:
    return [
        {"$match": {field: {"$nin": [None, ""]}}},
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
    ]


def _geocoded_total_pipeline() -> list[dict[str, Any]]:
    return [
        {"$match": _VALID_GEO_POINT_QUERY},
        {"$count": "total"},
    ]


def _map_items_pipeline(*, query: dict[str, Any], offset: int, limit: int) -> list[dict[str, Any]]:
    return [
        {"$match": query},
        {"$sort": {"published_at": -1}},
        {"$skip": offset},
        {"$limit": limit},
        {"$project": _NEWS_MAP_PROJECTION},
    ]


def _map_total_pipeline(*, query: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"$match": query},
        {"$count": "total"},
    ]


def _visible_news_query(query: dict[str, Any]) -> dict[str, Any]:
    visible_query = _merge_query(query, _ACTIVE_RECORD_QUERY)
    visibility_query = resolve_visible_generation_query(db)
    if not visibility_query:
        return visible_query
    return _merge_query(visible_query, visibility_query)


def _stats_response_from_facet(facet: dict[str, Any]) -> NewsStatsResponse:
    meta = facet.get("meta", [])
    meta_row = meta[0] if meta else {}
    total = int(meta_row.get("total", 0))
    geocoded_rows = facet.get("geocoded", [])
    geocoded_total = int(geocoded_rows[0].get("total", 0)) if geocoded_rows else 0
    last_3d_total = int(meta_row.get("last_3d_total", 0))
    active_sources = [
        str(source_id)
        for source_id in meta_row.get("active_sources", [])
        if source_id is not None
    ]

    return NewsStatsResponse(
        total=total,
        geocoded_total=geocoded_total,
        last_3d_total=last_3d_total,
        active_sources=len(active_sources),
        categories=_stats_buckets_from_rows(facet.get("categories", [])),
        districts=_stats_buckets_from_rows(facet.get("districts", [])),
    )


def _stats_buckets_from_rows(rows: list[dict[str, Any]]) -> list[StatsBucket]:
    return [
        StatsBucket(key=str(bucket["_id"]), count=int(bucket["count"]))
        for bucket in rows
    ]


def _build_news_query(
    *,
    source: Optional[str],
    category: Optional[str],
    categories: Optional[list[str]],
    district: Optional[str],
    districts: Optional[list[str]],
    search: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    geocoded_only: bool = False,
) -> dict[str, Any]:
    query: dict[str, Any] = {}

    if source:
        parsed = urlparse(source)
        source_value = (parsed.netloc or parsed.path or source).strip().lower()
        if source_value:
            query["kaynak_listesi"] = source_value

    requested_categories = _normalize_multi_values(categories)
    if category:
        requested_categories.append(category)

    normalized_categories: list[str] = []
    for value in requested_categories:
        category_enum = normalize_news_category(value)
        if category_enum is None:
            raise HTTPException(status_code=422, detail="Invalid category value")
        if category_enum.value not in normalized_categories:
            normalized_categories.append(category_enum.value)

    if normalized_categories:
        query["category_predicted"] = (
            normalized_categories[0]
            if len(normalized_categories) == 1
            else {"$in": normalized_categories}
        )

    requested_districts = _normalize_multi_values(districts)
    if district:
        requested_districts.append(district)

    normalized_districts: list[str] = []
    for value in requested_districts:
        district_enum = normalize_kocaeli_district(value)
        if district_enum is None:
            raise HTTPException(status_code=422, detail="Invalid district value")
        if district_enum.value not in normalized_districts:
            normalized_districts.append(district_enum.value)

    if normalized_districts:
        query["district_predicted"] = (
            normalized_districts[0]
            if len(normalized_districts) == 1
            else {"$in": normalized_districts}
        )

    published_range: dict[str, datetime] = {}
    normalized_date_from = _normalize_query_datetime(date_from)
    normalized_date_to = _normalize_query_datetime(date_to)
    if normalized_date_from is not None:
        published_range["$gte"] = normalized_date_from
    if normalized_date_to is not None:
        published_range["$lte"] = normalized_date_to
    if published_range:
        query["published_at"] = published_range

    cleaned_search = " ".join((search or "").split())
    if cleaned_search:
        query["$text"] = {"$search": cleaned_search}

    if geocoded_only:
        query = _merge_query(query, _VALID_GEO_POINT_QUERY)

    return query


def _isoformat_or_none(value: Any) -> str | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _extract_coordinates(doc: dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    point = doc.get("geocode_point")
    if not isinstance(point, dict):
        return None, None

    coordinates = point.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) != 2:
        return None, None

    longitude, latitude = coordinates
    if not isinstance(latitude, (int, float)) or isinstance(latitude, bool):
        return None, None
    if not isinstance(longitude, (int, float)) or isinstance(longitude, bool):
        return None, None

    return float(latitude), float(longitude)


def _has_valid_coordinates(doc: dict[str, Any]) -> bool:
    latitude, longitude = _extract_coordinates(doc)
    return latitude is not None and longitude is not None


def _source_domain(doc: dict[str, Any]) -> str:
    source_url = str(doc.get("source_url_snapshot") or "").strip()
    if source_url:
        parsed = urlparse(source_url)
        if parsed.netloc:
            return parsed.netloc

    source_domains = doc.get("kaynak_listesi")
    if isinstance(source_domains, list):
        for value in source_domains:
            if value:
                return str(value)

    canonical_url = str(doc.get("canonical_url") or "").strip()
    if canonical_url:
        parsed = urlparse(canonical_url)
        if parsed.netloc:
            return parsed.netloc

    return ""


def _source_site_url(domain: str, preferred_url: Any = None) -> str | None:
    preferred = str(preferred_url or "").strip()
    if preferred:
        parsed = urlparse(preferred)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return preferred

    domain = domain.strip()
    if not domain:
        return None

    if domain.startswith(("http://", "https://")):
        parsed = urlparse(domain)
        if parsed.netloc:
            return domain
        return None

    return f"https://{domain}"


def _source_site_key(domain: str) -> str:
    normalized = str(domain or "").strip()
    if not normalized:
        return ""

    parsed = urlparse(normalized)
    host = (parsed.netloc or parsed.path or normalized).strip().casefold()
    host = host.removeprefix("www.")
    return host.split(".", 1)[0] if "." in host else host


def _source_site_entry(doc: dict[str, Any], *, is_primary: bool) -> dict[str, Any] | None:
    domain = _source_domain(doc)
    url = _source_site_url(domain, doc.get("canonical_url") or doc.get("source_url_snapshot"))
    if not domain or not url:
        return None
    return {
        "domain": domain,
        "url": url,
        "is_primary": is_primary,
    }


def _source_sites(
    doc: dict[str, Any],
    *,
    related_source_docs: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    sites: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append_site(domain: str, url: str | None, *, is_primary: bool) -> None:
        clean_domain = str(domain or "").strip()
        clean_url = str(url or "").strip()
        if not clean_domain or not clean_url:
            return
        domain_key = _source_site_key(clean_domain) or _source_site_key(clean_url)
        if domain_key in seen:
            return
        seen.add(domain_key)
        sites.append(
            {
                "domain": clean_domain,
                "url": clean_url,
                "is_primary": is_primary,
            }
        )

    primary_entry = _source_site_entry(doc, is_primary=True)
    if primary_entry is not None:
        append_site(primary_entry["domain"], primary_entry["url"], is_primary=True)

    for related_doc in related_source_docs or []:
        related_entry = _source_site_entry(related_doc, is_primary=False)
        if related_entry is None:
            continue
        append_site(
            related_entry["domain"],
            related_entry["url"],
            is_primary=False,
        )

    for raw_domain in doc.get("kaynak_listesi") or []:
        domain = str(raw_domain or "").strip()
        if not domain:
            continue
        append_site(
            domain,
            _source_site_url(domain),
            is_primary=False,
        )

    return sites


def map_doc_to_news_list_item(doc: dict[str, Any]) -> NewsListItem:
    latitude, longitude = _extract_coordinates(doc)
    return NewsListItem(
        id=str(doc["_id"]),
        title=doc.get("title") or "",
        summary=clean_news_text(doc.get("summary")),
        source_name=doc.get("source_name_snapshot") or "",
        source_domain=_source_domain(doc),
        source_base_url=doc.get("source_url_snapshot"),
        url=doc.get("canonical_url") or "",
        published_at_raw=_isoformat_or_none(doc.get("published_at")),
        category=doc.get("category_predicted"),
        category_confidence=doc.get("category_confidence"),
        district=doc.get("district_predicted"),
        district_confidence=doc.get("district_confidence"),
        geocode_status=doc.get("geocode_status"),
        latitude=latitude,
        longitude=longitude,
        source_domains=[str(item) for item in doc.get("kaynak_listesi") or [] if item],
        scraped_at=_isoformat_or_none(doc.get("created_at")),
    )


def map_doc_to_news_map_item(doc: dict[str, Any]) -> NewsMapItem:
    latitude, longitude = _extract_coordinates(doc)
    if latitude is None or longitude is None:
        raise ValueError("Document does not include valid coordinates")

    return NewsMapItem(
        id=str(doc["_id"]),
        title=doc.get("title") or "",
        summary=clean_news_text(doc.get("summary")),
        source_name=doc.get("source_name_snapshot") or "",
        source_domain=_source_domain(doc),
        url=doc.get("canonical_url") or "",
        published_at_raw=_isoformat_or_none(doc.get("published_at")),
        category=doc.get("category_predicted"),
        category_confidence=doc.get("category_confidence"),
        district=doc.get("district_predicted"),
        geocode_status=doc.get("geocode_status") or "failed",
        latitude=latitude,
        longitude=longitude,
    )


def map_doc_to_news_response(
    doc: dict[str, Any],
    *,
    related_source_docs: Optional[list[dict[str, Any]]] = None,
) -> NewsResponse:
    item = map_doc_to_news_list_item(doc)
    return NewsResponse(
        **item.model_dump(),
        content_text=clean_news_text(doc.get("body")) or "",
        location_text_extracted=clean_news_text(doc.get("location_text_extracted")),
        source_sites=_source_sites(doc, related_source_docs=related_source_docs),
    )


@router.get("", response_model=NewsListResponse)
def list_news(
    source: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    categories: Optional[list[str]] = Query(default=None),
    district: Optional[str] = Query(default=None),
    districts: Optional[list[str]] = Query(default=None),
    search: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> NewsListResponse:
    query = _visible_news_query(
        _build_news_query(
        source=source,
        category=category,
        categories=categories,
        district=district,
        districts=districts,
        search=search,
        date_from=date_from,
        date_to=date_to,
        )
    )

    collection = db["source_records"]
    total = collection.count_documents(query)
    docs = (
        collection.find(query, _NEWS_LIST_PROJECTION)
        .sort("published_at", -1)
        .skip(offset)
        .limit(limit)
    )
    items = [map_doc_to_news_list_item(doc) for doc in docs]
    return NewsListResponse(items=items, total=total)


@router.get("/map", response_model=NewsMapResponse)
def list_news_map(
    source: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    categories: Optional[list[str]] = Query(default=None),
    district: Optional[str] = Query(default=None),
    districts: Optional[list[str]] = Query(default=None),
    search: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
) -> NewsMapResponse:
    query = _visible_news_query(
        _build_news_query(
        source=source,
        category=category,
        categories=categories,
        district=district,
        districts=districts,
        search=search,
        date_from=date_from,
        date_to=date_to,
        geocoded_only=True,
        )
    )

    collection = db["source_records"]
    total = collection.count_documents(query)
    docs = (
        collection.find(query, _NEWS_MAP_PROJECTION)
        .sort("published_at", -1)
        .skip(offset)
        .limit(limit)
    )
    items: list[NewsMapItem] = []
    for doc in docs:
        if not _has_valid_coordinates(doc):
            continue
        items.append(map_doc_to_news_map_item(doc))

    return NewsMapResponse(items=items, total=total)


@router.get("/dashboard", response_model=NewsDashboardResponse)
def get_news_dashboard(
    source: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    categories: Optional[list[str]] = Query(default=None),
    district: Optional[str] = Query(default=None),
    districts: Optional[list[str]] = Query(default=None),
    search: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
) -> NewsDashboardResponse:
    base_query = _build_news_query(
        source=source,
        category=category,
        categories=categories,
        district=district,
        districts=districts,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    current_query = _visible_news_query(base_query)
    current_map_query = _merge_query(current_query, _VALID_GEO_POINT_QUERY)
    category_query = _visible_news_query(
        _build_news_query(
            source=source,
            category=None,
            categories=None,
            district=district,
            districts=districts,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
    )
    district_query = _visible_news_query(
        _build_news_query(
            source=source,
            category=category,
            categories=categories,
            district=None,
            districts=None,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
    )

    collection = db["source_records"]
    now = datetime.now(timezone.utc)
    last_3d_cutoff = now - timedelta(days=3)
    facet = (
        next(
            iter(
                collection.aggregate(
                    [
                        {
                            "$facet": {
                                "stats_meta": [
                                    {"$match": current_query},
                                    *_stats_meta_pipeline(last_3d_cutoff=last_3d_cutoff),
                                ],
                                "stats_categories": [
                                    {"$match": current_query},
                                    *_bucket_pipeline("category_predicted"),
                                ],
                                "stats_districts": [
                                    {"$match": current_query},
                                    *_bucket_pipeline("district_predicted"),
                                ],
                                "stats_geocoded": [
                                    {"$match": current_query},
                                    *_geocoded_total_pipeline(),
                                ],
                                "category_facets": [
                                    {"$match": category_query},
                                    *_bucket_pipeline("category_predicted"),
                                ],
                                "district_facets": [
                                    {"$match": district_query},
                                    *_bucket_pipeline("district_predicted"),
                                ],
                                "map_total": _map_total_pipeline(query=current_map_query),
                                "map_items": _map_items_pipeline(
                                    query=current_map_query,
                                    offset=offset,
                                    limit=limit,
                                ),
                            }
                        }
                    ]
                )
            ),
            None,
        )
        or {}
    )

    stats = _stats_response_from_facet(
        {
            "meta": facet.get("stats_meta", []),
            "categories": facet.get("stats_categories", []),
            "districts": facet.get("stats_districts", []),
            "geocoded": facet.get("stats_geocoded", []),
        }
    )
    map_total_rows = facet.get("map_total", [])
    map_total = int(map_total_rows[0].get("total", 0)) if map_total_rows else 0
    map_items = [
        map_doc_to_news_map_item(doc)
        for doc in facet.get("map_items", [])
        if _has_valid_coordinates(doc)
    ]

    return NewsDashboardResponse(
        map=NewsMapResponse(items=map_items, total=map_total),
        stats=stats,
        category_facets=_stats_buckets_from_rows(facet.get("category_facets", [])),
        district_facets=_stats_buckets_from_rows(facet.get("district_facets", [])),
    )


@router.get("/stats", response_model=NewsStatsResponse)
def get_news_stats(
    source: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    categories: Optional[list[str]] = Query(default=None),
    district: Optional[str] = Query(default=None),
    districts: Optional[list[str]] = Query(default=None),
    search: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
) -> NewsStatsResponse:
    query = _visible_news_query(
        _build_news_query(
        source=source,
        category=category,
        categories=categories,
        district=district,
        districts=districts,
        search=search,
        date_from=date_from,
        date_to=date_to,
        )
    )

    collection = db["source_records"]
    now = datetime.now(timezone.utc)
    last_3d_cutoff = now - timedelta(days=3)
    facet = (
        next(
            iter(
                collection.aggregate(
                    _stats_facet_pipeline(query, last_3d_cutoff=last_3d_cutoff)
                )
            ),
            None,
        )
        or {}
    )

    return _stats_response_from_facet(facet)


@router.get("/{news_id}", response_model=NewsResponse)
def get_news_detail(news_id: str) -> JSONResponse:
    return JSONResponse(content=_get_news_detail_payload(news_id).model_dump(mode="json"))


def _get_news_detail_payload(news_id: str) -> NewsResponse:
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=400, detail="Invalid news id")

    detail_query: dict[str, Any] = {"_id": ObjectId(news_id)}
    detail_query = _merge_query(detail_query, _visible_news_query({}))
    doc = db["source_records"].find_one(detail_query)
    if doc is None:
        raise HTTPException(status_code=404, detail="News not found")

    related_query: dict[str, Any] = {
        "duplicate_of_record_id": doc["_id"],
        "record_status": "merged_duplicate",
    }
    dataset_generation = doc.get("dataset_generation")
    if dataset_generation is not None:
        related_query["dataset_generation"] = dataset_generation
    related_source_docs = list(db["source_records"].find(related_query))

    return map_doc_to_news_response(
        doc,
        related_source_docs=related_source_docs,
    )
