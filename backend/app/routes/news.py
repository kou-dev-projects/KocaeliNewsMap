from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Path, Query

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


def _extract_domain(url: Optional[str]) -> str:
    if not url:
        return ""
    return urlparse(url).netloc


def _serialize_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _normalize_query_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _extract_coordinates(doc: dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    point = doc.get("geocode_point")
    if not isinstance(point, dict):
        return None, None

    coordinates = point.get("coordinates")
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) != 2:
        return None, None

    try:
        longitude = float(coordinates[0])
        latitude = float(coordinates[1])
    except (TypeError, ValueError):
        return None, None

    return latitude, longitude


def _source_domains(doc: dict[str, Any]) -> list[str]:
    values = doc.get("kaynak_listesi")
    if not isinstance(values, list):
        values = []

    domains = [
        value.strip()
        for value in values
        if isinstance(value, str) and value.strip()
    ]
    if domains:
        return domains

    fallback = _extract_domain(doc.get("source_url_snapshot"))
    return [fallback] if fallback else []


def _image_url(doc: dict[str, Any]) -> Optional[str]:
    for field in ("image_url", "image_url_snapshot", "hero_image_url", "cover_image_url"):
        value = doc.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_valid_coordinates(doc: dict[str, Any]) -> bool:
    latitude, longitude = _extract_coordinates(doc)
    return latitude is not None and longitude is not None


def _build_news_query(
    *,
    source: Optional[str],
    category: Optional[str],
    district: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    geocoded_only: bool = False,
) -> dict[str, Any]:
    query: dict[str, Any] = {}

    if source:
        query["source_name_snapshot"] = source

    if category:
        category_enum = normalize_news_category(category)
        if category_enum is None:
            raise HTTPException(status_code=422, detail="Invalid category value")
        query["category_predicted"] = category_enum.value

    if district:
        district_enum = normalize_kocaeli_district(district)
        if district_enum is None:
            raise HTTPException(status_code=422, detail="Invalid district value")
        query["district_predicted"] = district_enum.value

    published_range: dict[str, datetime] = {}
    normalized_date_from = _normalize_query_datetime(date_from)
    normalized_date_to = _normalize_query_datetime(date_to)
    if normalized_date_from is not None:
        published_range["$gte"] = normalized_date_from
    if normalized_date_to is not None:
        published_range["$lte"] = normalized_date_to
    if published_range:
        query["published_at"] = published_range

    if geocoded_only:
        query["geocode_point"] = {"$ne": None}

    return query


def map_doc_to_news_list_item(doc: dict[str, Any]) -> NewsListItem:
    source_base_url = doc.get("source_url_snapshot")
    latitude, longitude = _extract_coordinates(doc)

    return NewsListItem(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        summary=doc.get("summary"),
        source_name=doc.get("source_name_snapshot", ""),
        source_domain=_extract_domain(source_base_url),
        source_base_url=source_base_url,
        url=doc.get("canonical_url", ""),
        image_url=_image_url(doc),
        published_at_raw=_serialize_datetime(doc.get("published_at")),
        category=doc.get("category_predicted"),
        category_confidence=doc.get("category_confidence"),
        district=doc.get("district_predicted"),
        district_confidence=doc.get("district_confidence"),
        geocode_status=doc.get("geocode_status"),
        latitude=latitude,
        longitude=longitude,
        source_domains=_source_domains(doc),
        scraped_at=_serialize_datetime(doc.get("created_at")),
    )


def map_doc_to_news_response(doc: dict[str, Any]) -> NewsResponse:
    source_base_url = doc.get("source_url_snapshot")
    latitude, longitude = _extract_coordinates(doc)

    return NewsResponse(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        summary=doc.get("summary"),
        content_text=doc.get("body", ""),
        source_name=doc.get("source_name_snapshot", ""),
        source_domain=_extract_domain(source_base_url),
        source_base_url=source_base_url,
        url=doc.get("canonical_url", ""),
        image_url=_image_url(doc),
        published_at_raw=_serialize_datetime(doc.get("published_at")),
        category=doc.get("category_predicted"),
        category_confidence=doc.get("category_confidence"),
        district=doc.get("district_predicted"),
        district_confidence=doc.get("district_confidence"),
        geocode_status=doc.get("geocode_status"),
        latitude=latitude,
        longitude=longitude,
        source_domains=_source_domains(doc),
        scraped_at=_serialize_datetime(doc.get("created_at")),
    )


def map_doc_to_news_map_item(doc: dict[str, Any]) -> NewsMapItem:
    source_base_url = doc.get("source_url_snapshot")
    latitude, longitude = _extract_coordinates(doc)
    if latitude is None or longitude is None:
        raise ValueError("missing_geocode_point")

    return NewsMapItem(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        summary=doc.get("summary"),
        source_name=doc.get("source_name_snapshot", ""),
        source_domain=_extract_domain(source_base_url),
        url=doc.get("canonical_url", ""),
        published_at_raw=_serialize_datetime(doc.get("published_at")),
        category=doc.get("category_predicted"),
        category_confidence=doc.get("category_confidence"),
        district=doc.get("district_predicted"),
        geocode_status=doc.get("geocode_status", "resolved"),
        latitude=latitude,
        longitude=longitude,
    )


def _count_buckets(docs: list[dict[str, Any]], field: str) -> list[StatsBucket]:
    counts = Counter(
        str(value)
        for doc in docs
        if (value := doc.get(field)) not in {None, ""}
    )
    return [
        StatsBucket(key=key, count=count)
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


@router.get("", response_model=NewsListResponse)
def list_news(
    source: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = _build_news_query(
        source=source,
        category=category,
        district=district,
        date_from=date_from,
        date_to=date_to,
    )

    collection = db["source_records"]
    total = collection.count_documents(query)
    docs = collection.find(query).sort("published_at", -1).skip(offset).limit(limit)
    items = [map_doc_to_news_list_item(doc) for doc in docs]

    return NewsListResponse(items=items, total=total)


@router.get("/map", response_model=NewsMapResponse)
def list_news_map(
    source: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
):
    query = _build_news_query(
        source=source,
        category=category,
        district=district,
        date_from=date_from,
        date_to=date_to,
        geocoded_only=True,
    )

    collection = db["source_records"]
    total = sum(1 for doc in collection.find(query) if _has_valid_coordinates(doc))
    docs = collection.find(query).sort("published_at", -1).skip(offset).limit(limit)
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
    district: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
):
    query = _build_news_query(
        source=source,
        category=category,
        district=district,
        date_from=date_from,
        date_to=date_to,
    )

    collection = db["source_records"]
    docs = list(collection.find(query))
    now = datetime.now(timezone.utc)
    last_24h_cutoff = now - timedelta(hours=24)

    geocoded_total = sum(1 for doc in docs if doc.get("geocode_point") is not None)
    last_24h_total = 0
    for doc in docs:
        published_at = doc.get("published_at")
        if isinstance(published_at, datetime):
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            if published_at >= last_24h_cutoff:
                last_24h_total += 1

    active_sources = len(
        {
            str(source_id)
            for doc in docs
            if (source_id := doc.get("source_id")) is not None
        }
    )

    return NewsStatsResponse(
        total=len(docs),
        geocoded_total=geocoded_total,
        last_24h_total=last_24h_total,
        active_sources=active_sources,
        categories=_count_buckets(docs, "category_predicted"),
        districts=_count_buckets(docs, "district_predicted"),
    )


@router.get("/{id}", response_model=NewsResponse)
def get_news_detail(
    id: str = Path(..., description="MongoDB ObjectId"),
):
    try:
        object_id = ObjectId(id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid news id format",
        )

    collection = db["source_records"]
    doc = collection.find_one({"_id": object_id})

    if doc is None:
        raise HTTPException(
            status_code=404,
            detail="News not found",
        )

    return map_doc_to_news_response(doc)
