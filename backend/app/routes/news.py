from typing import Any, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Query

from app.db.database import db
from app.schemas import NewsListItem, NewsListResponse, NewsResponse


router = APIRouter(prefix="/news", tags=["news"])


def _extract_domain(url: Optional[str]) -> str:
    if not url:
        return ""
    return urlparse(url).netloc


def map_doc_to_news_list_item(doc: dict[str, Any]) -> NewsListItem:
    source_base_url = doc.get("source_url_snapshot")

    return NewsListItem(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        summary=doc.get("summary"),
        source_name=doc.get("source_name_snapshot", ""),
        source_domain=_extract_domain(source_base_url),
        source_base_url=source_base_url,
        url=doc.get("canonical_url", ""),
        image_url=None,
        published_at_raw=str(doc.get("published_at")) if doc.get("published_at") is not None else None,
        scraped_at=str(doc.get("created_at")) if doc.get("created_at") is not None else None,
    )


def map_doc_to_news_response(doc: dict[str, Any]) -> NewsResponse:
    source_base_url = doc.get("source_url_snapshot")

    return NewsResponse(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        summary=doc.get("summary"),
        content_text=doc.get("body", ""),
        source_name=doc.get("source_name_snapshot", ""),
        source_domain=_extract_domain(source_base_url),
        source_base_url=source_base_url,
        url=doc.get("canonical_url", ""),
        image_url=None,
        published_at_raw=str(doc.get("published_at")) if doc.get("published_at") is not None else None,
        scraped_at=str(doc.get("created_at")) if doc.get("created_at") is not None else None,
    )


@router.get("", response_model=NewsListResponse)
def list_news(
    source: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query: dict[str, Any] = {}

    if source:
        query["source_name_snapshot"] = source

    collection = db["source_records"]
    total = collection.count_documents(query)

    docs = collection.find(query).sort("published_at", -1).skip(offset).limit(limit)

    items = [map_doc_to_news_list_item(doc) for doc in docs]

    return NewsListResponse(
        items=items,
        total=total,
    )
