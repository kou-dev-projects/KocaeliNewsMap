from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.routes.news import get_news_detail, get_news_stats, list_news, list_news_map


class FakeCursor:
    def __init__(self, docs: list[dict]):
        self._docs = list(docs)

    def sort(self, field: str, direction: int):
        self._docs.sort(
            key=lambda doc: doc.get(field) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=direction < 0,
        )
        return self

    def skip(self, offset: int):
        self._docs = self._docs[offset:]
        return self

    def limit(self, limit: int):
        self._docs = self._docs[:limit]
        return self

    def __iter__(self):
        return iter(self._docs)


class FakeCollection:
    def __init__(self, docs: list[dict]):
        self._docs = list(docs)

    def _matches(self, doc: dict, query: dict) -> bool:
        for field, expected in query.items():
            actual = doc.get(field)
            if isinstance(expected, dict):
                if "$gte" in expected and (actual is None or actual < expected["$gte"]):
                    return False
                if "$lte" in expected and (actual is None or actual > expected["$lte"]):
                    return False
                if "$ne" in expected and actual == expected["$ne"]:
                    return False
                continue
            if actual != expected:
                return False
        return True

    def count_documents(self, query: dict) -> int:
        return len([doc for doc in self._docs if self._matches(doc, query)])

    def find(self, query: dict, projection=None):
        docs = [doc for doc in self._docs if self._matches(doc, query)]
        return FakeCursor(docs)

    def find_one(self, query: dict):
        for doc in self._docs:
            if self._matches(doc, query):
                return doc
        return None


class FakeDB:
    def __init__(self, source_records: list[dict]):
        self._collections = {
            "source_records": FakeCollection(source_records),
        }

    def __getitem__(self, name: str):
        return self._collections[name]


def _doc(
    object_id: ObjectId,
    *,
    title: str,
    category: str,
    district: str | None,
    published_at: datetime,
    geocoded: bool,
):
    point = None
    if geocoded:
        point = {"type": "Point", "coordinates": [29.94, 40.76]}

    return {
        "_id": object_id,
        "source_id": ObjectId("65f1b5f1b5f1b5f1b5f1b5f1"),
        "canonical_url": f"https://example.com/{object_id}",
        "title": title,
        "body": f"{title} body",
        "summary": f"{title} summary",
        "published_at": published_at,
        "created_at": published_at + timedelta(minutes=5),
        "source_name_snapshot": "Ozgur Kocaeli",
        "source_url_snapshot": "https://www.ozgurkocaeli.com.tr",
        "image_url": "https://cdn.example.com/news.jpg",
        "category_predicted": category,
        "category_confidence": 0.92,
        "district_predicted": district,
        "district_confidence": 0.88 if district else None,
        "location_text_extracted": district,
        "geocode_status": "resolved" if geocoded else "failed",
        "geocode_point": point,
        "kaynak_listesi": ["ozgurkocaeli.com.tr"],
    }


@pytest.fixture
def sample_docs():
    now = datetime.now(timezone.utc)
    return [
        _doc(
            ObjectId("65f1b5f1b5f1b5f1b5f1b5f2"),
            title="Izmit yangin",
            category="yangin",
            district="izmit",
            published_at=now - timedelta(hours=2),
            geocoded=True,
        ),
        _doc(
            ObjectId("65f1b5f1b5f1b5f1b5f1b5f3"),
            title="Gebze trafik",
            category="trafik_kazasi",
            district="gebze",
            published_at=now - timedelta(days=2),
            geocoded=False,
        ),
    ]


def test_list_news_returns_enriched_items(monkeypatch, sample_docs):
    monkeypatch.setattr("app.routes.news.db", FakeDB(sample_docs))

    response = list_news(
        source=None,
        category=None,
        district=None,
        date_from=None,
        date_to=None,
        limit=20,
        offset=0,
    )

    assert response.total == 2
    assert response.items[0].category == "yangin"
    assert response.items[0].district == "izmit"
    assert response.items[0].latitude == 40.76
    assert response.items[0].longitude == 29.94
    assert response.items[0].image_url == "https://cdn.example.com/news.jpg"
    assert response.items[0].source_domains == ["ozgurkocaeli.com.tr"]


def test_list_news_honors_date_filters(monkeypatch, sample_docs):
    monkeypatch.setattr("app.routes.news.db", FakeDB(sample_docs))
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)

    response = list_news(
        source=None,
        category=None,
        district=None,
        date_from=cutoff,
        date_to=None,
        limit=20,
        offset=0,
    )

    assert response.total == 1
    assert response.items[0].district == "izmit"


def test_list_news_map_returns_only_geocoded_items(monkeypatch, sample_docs):
    monkeypatch.setattr("app.routes.news.db", FakeDB(sample_docs))

    response = list_news_map(
        source=None,
        category=None,
        district=None,
        date_from=None,
        date_to=None,
        limit=500,
        offset=0,
    )

    assert response.total == 1
    assert response.items[0].latitude == 40.76
    assert response.items[0].category == "yangin"


def test_list_news_map_skips_invalid_geocode_shape(monkeypatch, sample_docs):
    invalid_doc = dict(sample_docs[0])
    invalid_doc["_id"] = ObjectId("65f1b5f1b5f1b5f1b5f1b5f4")
    invalid_doc["geocode_point"] = {"type": "Point", "coordinates": ["bad", 40.76]}
    monkeypatch.setattr("app.routes.news.db", FakeDB([invalid_doc, *sample_docs]))

    response = list_news_map(
        source=None,
        category=None,
        district=None,
        date_from=None,
        date_to=None,
        limit=500,
        offset=0,
    )

    assert response.total == 1
    assert len(response.items) == 1


def test_get_news_stats_returns_facets(monkeypatch, sample_docs):
    monkeypatch.setattr("app.routes.news.db", FakeDB(sample_docs))

    response = get_news_stats(
        source=None,
        category=None,
        district=None,
        date_from=None,
        date_to=None,
    )

    assert response.total == 2
    assert response.geocoded_total == 1
    assert response.last_3d_total == 2
    assert response.active_sources == 1
    assert response.categories[0].key in {"trafik_kazasi", "yangin"}
    assert {bucket.key for bucket in response.districts} == {"gebze", "izmit"}


def test_get_news_detail_returns_enriched_payload(monkeypatch, sample_docs):
    monkeypatch.setattr("app.routes.news.db", FakeDB(sample_docs))

    response = get_news_detail(str(sample_docs[0]["_id"]))

    assert response.category == "yangin"
    assert response.district == "izmit"
    assert response.latitude == 40.76
    assert response.image_url == "https://cdn.example.com/news.jpg"
    assert response.content_text == "Izmit yangin body"


def test_get_news_detail_rejects_invalid_object_id(monkeypatch, sample_docs):
    monkeypatch.setattr("app.routes.news.db", FakeDB(sample_docs))

    with pytest.raises(HTTPException) as exc_info:
        get_news_detail("invalid")

    assert exc_info.value.status_code == 400
