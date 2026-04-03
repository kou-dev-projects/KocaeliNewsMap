from __future__ import annotations

import re
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

    def _extract_value(self, doc: dict, field: str):
        current = doc
        for part in field.split("."):
            if isinstance(current, dict):
                current = current.get(part)
                continue
            if isinstance(current, list) and part.isdigit():
                index = int(part)
                if index >= len(current):
                    return None
                current = current[index]
                continue
            return None
        return current

    def _matches(self, doc: dict, query: dict) -> bool:
        for field, expected in query.items():
            if field == "$or":
                return any(self._matches(doc, branch) for branch in expected)
            if field == "$text":
                search_value = str(expected.get("$search", "")).casefold()
                haystack = " ".join(
                    str(doc.get(name, "") or "")
                    for name in (
                        "title",
                        "summary",
                        "body",
                        "source_name_snapshot",
                        "source_url_snapshot",
                        "district_predicted",
                        "location_text_extracted",
                    )
                ).casefold()
                if search_value not in haystack:
                    return False
                continue

            actual = self._extract_value(doc, field)
            if isinstance(expected, dict):
                if "$gte" in expected and (actual is None or actual < expected["$gte"]):
                    return False
                if "$lte" in expected and (actual is None or actual > expected["$lte"]):
                    return False
                if "$ne" in expected and actual == expected["$ne"]:
                    return False
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                if "$nin" in expected and actual in expected["$nin"]:
                    return False
                if "$type" in expected:
                    if expected["$type"] == "number":
                        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
                            return False
                    else:
                        return False
                if "$regex" in expected:
                    flags = re.IGNORECASE if "i" in str(expected.get("$options", "")) else 0
                    if actual is None or re.search(expected["$regex"], str(actual), flags=flags) is None:
                        return False
                continue
            if actual != expected:
                return False
        return True

    def _evaluate_expression(self, doc: dict, expression):
        if isinstance(expression, str) and expression.startswith("$"):
            return self._extract_value(doc, expression[1:])
        if isinstance(expression, dict):
            if "$cond" in expression:
                condition, truthy, falsy = expression["$cond"]
                return (
                    self._evaluate_expression(doc, truthy)
                    if self._evaluate_expression(doc, condition)
                    else self._evaluate_expression(doc, falsy)
                )
            if "$gte" in expression:
                left, right = expression["$gte"]
                left_value = self._evaluate_expression(doc, left)
                right_value = self._evaluate_expression(doc, right)
                return (
                    left_value is not None
                    and right_value is not None
                    and left_value >= right_value
                )
        return expression

    def _apply_pipeline(self, docs: list[dict], pipeline: list[dict]) -> list[dict]:
        current = list(docs)

        for stage in pipeline:
            if "$match" in stage:
                current = [doc for doc in current if self._matches(doc, stage["$match"])]
                continue
            if "$group" in stage:
                spec = stage["$group"]
                grouped: dict[object, dict] = {}

                for doc in current:
                    group_key = self._evaluate_expression(doc, spec["_id"])
                    bucket = grouped.setdefault(group_key, {"_id": group_key})

                    for field, accumulator in spec.items():
                        if field == "_id":
                            continue
                        if "$sum" in accumulator:
                            bucket[field] = bucket.get(field, 0) + int(
                                self._evaluate_expression(doc, accumulator["$sum"])
                            )
                            continue
                        if "$addToSet" in accumulator:
                            values = bucket.setdefault(field, [])
                            candidate = self._evaluate_expression(
                                doc, accumulator["$addToSet"]
                            )
                            if candidate not in values:
                                values.append(candidate)
                            continue
                        raise NotImplementedError(accumulator)

                current = list(grouped.values())
                continue
            if "$sort" in stage:
                sort_spec = stage["$sort"]
                for field, direction in reversed(list(sort_spec.items())):
                    current.sort(
                        key=lambda doc: doc.get(field),
                        reverse=direction < 0,
                    )
                continue
            if "$count" in stage:
                current = [{stage["$count"]: len(current)}]
                continue
            raise NotImplementedError(stage)

        return current

    def aggregate(self, pipeline: list[dict]):
        current = list(self._docs)

        for stage in pipeline:
            if "$match" in stage:
                current = [doc for doc in current if self._matches(doc, stage["$match"])]
                continue
            if "$facet" in stage:
                return [
                    {
                        name: self._apply_pipeline(current, facet_pipeline)
                        for name, facet_pipeline in stage["$facet"].items()
                    }
                ]
            raise NotImplementedError(stage)

        return current

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
        categories=None,
        district=None,
        districts=None,
        search=None,
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
        categories=None,
        district=None,
        districts=None,
        search=None,
        date_from=cutoff,
        date_to=None,
        limit=20,
        offset=0,
    )

    assert response.total == 1
    assert response.items[0].district == "izmit"


def test_list_news_supports_multi_filters_and_search(monkeypatch, sample_docs):
    monkeypatch.setattr("app.routes.news.db", FakeDB(sample_docs))

    response = list_news(
        source=None,
        category=None,
        categories=["yangin,hirsizlik"],
        district=None,
        districts=["izmit", "gebze"],
        search="yangin",
        date_from=None,
        date_to=None,
        limit=20,
        offset=0,
    )

    assert response.total == 1
    assert response.items[0].title == "Izmit yangin"


def test_list_news_map_returns_only_geocoded_items(monkeypatch, sample_docs):
    monkeypatch.setattr("app.routes.news.db", FakeDB(sample_docs))
    response = list_news_map(
        source=None,
        category=None,
        categories=None,
        district=None,
        districts=None,
        search=None,
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
        categories=None,
        district=None,
        districts=None,
        search=None,
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
        categories=None,
        district=None,
        districts=None,
        search=None,
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
