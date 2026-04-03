from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.db.database import db
from app.domain.enums import normalize_kocaeli_district, normalize_news_category
from app.schemas import (
    NewsListItem,
    NewsListResponse,
    NewsMapItem,
    NewsMapResponse,
    NewsResponse,
    NewsStatsResponse,
    StatsBucket,
)

router = APIRouter(prefix="/news", tags=["news"])

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
    "image_url": 1,
    "image_url_snapshot": 1,
    "hero_image_url": 1,
    "cover_image_url": 1,
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
                "meta": [
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
                ],
                "categories": [
                    {"$match": {"category_predicted": {"$nin": [None, ""]}}},
                    {"$group": {"_id": "$category_predicted", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1, "_id": 1}},
                ],
                "districts": [
                    {"$match": {"district_predicted": {"$nin": [None, ""]}}},
                    {"$group": {"_id": "$district_predicted", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1, "_id": 1}},
                ],
                "geocoded": [
                    {"$match": _VALID_GEO_POINT_QUERY},
                    {"$count": "total"},
                ],
            }
        },
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


def _image_url(doc: dict[str, Any]) -> str | None:
    for key in (
        "image_url",
        "image_url_snapshot",
        "hero_image_url",
        "cover_image_url",
    ):
        value = doc.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def map_doc_to_news_list_item(doc: dict[str, Any]) -> NewsListItem:
    latitude, longitude = _extract_coordinates(doc)
    return NewsListItem(
        id=str(doc["_id"]),
        title=doc.get("title") or "",
        summary=doc.get("summary"),
        source_name=doc.get("source_name_snapshot") or "",
        source_domain=_source_domain(doc),
        source_base_url=doc.get("source_url_snapshot"),
        url=doc.get("canonical_url") or "",
        image_url=_image_url(doc),
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
        summary=doc.get("summary"),
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


def map_doc_to_news_response(doc: dict[str, Any]) -> NewsResponse:
    item = map_doc_to_news_list_item(doc)
    return NewsResponse(**item.model_dump(), content_text=doc.get("body") or "")


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
    query = _build_news_query(
        source=source,
        category=category,
        categories=categories,
        district=district,
        districts=districts,
        search=search,
        date_from=date_from,
        date_to=date_to,
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
    query = _build_news_query(
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
    query = _build_news_query(
        source=source,
        category=category,
        categories=categories,
        district=district,
        districts=districts,
        search=search,
        date_from=date_from,
        date_to=date_to,
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

    meta = facet.get("meta", [])
    meta_row = meta[0] if meta else {}
    total = int(meta_row.get("total", 0))
    geocoded_rows = facet.get("geocoded", [])
    geocoded_total = (
        int(geocoded_rows[0].get("total", 0)) if geocoded_rows else 0
    )
    last_3d_total = int(meta_row.get("last_3d_total", 0))
    active_sources = [
        str(source_id)
        for source_id in meta_row.get("active_sources", [])
        if source_id is not None
    ]
    categories_rows = facet.get("categories", [])
    districts_rows = facet.get("districts", [])

    return NewsStatsResponse(
        total=total,
        geocoded_total=geocoded_total,
        last_3d_total=last_3d_total,
        active_sources=len(active_sources),
        categories=[
            StatsBucket(key=str(bucket["_id"]), count=int(bucket["count"]))
            for bucket in categories_rows
        ],
        districts=[
            StatsBucket(key=str(bucket["_id"]), count=int(bucket["count"]))
            for bucket in districts_rows
        ],
    )


@router.get("/{news_id}", response_model=NewsResponse)
def get_news_detail(news_id: str) -> NewsResponse:
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=400, detail="Invalid news id")

    doc = db["source_records"].find_one({"_id": ObjectId(news_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="News not found")

    return map_doc_to_news_response(doc)
