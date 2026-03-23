import pytest

from app.services.mcp.config import MCPConfig
from app.services.mcp.dead_letter import DeadLetterStore
from app.services.mcp.idempotency import IdempotencyStore
from app.services.mcp.queue import WriteQueue
from app.services.mcp.schemas import NewsWriteRequest, WriteStatus
from app.services.mcp.write_service import NewsWriteService


class DummyIdempotency:
    def __init__(self):
        self.processed = {}

    def is_duplicate(self, key: str) -> bool:
        return key in self.processed

    def get_existing_id(self, key: str):
        return self.processed.get(key)

    def mark_processed(self, key: str, news_id: str) -> None:
        self.processed[key] = news_id


class DummyMaterializer:
    def materialize(self, *, raw_document, source_document, now=None):
        return {
            "raw_document_id": raw_document["_id"],
            "source_id": source_document["_id"],
            "canonical_url": raw_document["canonical_url"],
            "title": raw_document["title_raw"],
            "body": raw_document["content_raw"] or raw_document["text_raw"],
            "published_at": raw_document["published_at_raw"] or raw_document["scraped_at"],
            "category_predicted": "unknown",
            "district_predicted": None,
            "location_text_extracted": None,
            "geocode_status": "not_needed",
            "pipeline_status": "classified",
            "record_status": "active",
            "schema_version": "1.0",
            "updated_at": raw_document["updated_at"],
        }


def _cfg() -> MCPConfig:
    return MCPConfig(
        redis_url="redis://localhost:6379/0",
        mongo_url="mongodb://localhost:27017",
        mongo_db="kocaeli_news",
        lease_ttl_seconds=300,
        idempotency_ttl_seconds=86400,
        max_queue_size=10,
        max_queue_retries=3,
        fail_closed=True,
        mcp_host="0.0.0.0",
        mcp_port=8001,
        worker_id="test-worker",
    )


def _req(url: str = "https://example.com/a") -> NewsWriteRequest:
    return NewsWriteRequest(
        title="Test haber",
        url=url,
        source="example.com",
        content="icerik",
    )


def test_mock_insert_marks_idempotency():
    idem = DummyIdempotency()
    svc = NewsWriteService(
        idempotency=idem,
        queue=WriteQueue(10, 3),
        dead_letter=DeadLetterStore(),
        config=_cfg(),
        mongo_client=None,
        materializer=DummyMaterializer(),
    )

    result = svc.write(_req())

    assert result.status == WriteStatus.INSERTED
    assert result.news_id is not None
    assert idem.is_duplicate(result.idempotency_key) is True


def test_duplicate_returns_duplicate_merged():
    idem = DummyIdempotency()
    req = _req()
    idem_key = req.idempotency_key()
    idem.mark_processed(idem_key, "news_123")

    svc = NewsWriteService(
        idempotency=idem,
        queue=WriteQueue(10, 3),
        dead_letter=DeadLetterStore(),
        config=_cfg(),
        mongo_client=None,
        materializer=DummyMaterializer(),
    )

    result = svc.write(req)

    assert result.status == WriteStatus.DUPLICATE_MERGED
    assert result.news_id == "news_123"
    assert result.was_duplicate is True


def test_fail_closed_queues_when_mongo_write_fails():
    idem = DummyIdempotency()
    queue = WriteQueue(10, 3)
    dead = DeadLetterStore()
    svc = NewsWriteService(
        idempotency=idem,
        queue=queue,
        dead_letter=dead,
        config=_cfg(),
        mongo_client="not-none",
        materializer=DummyMaterializer(),
    )

    svc._mongo_write = lambda request, idem_key: (_ for _ in ()).throw(RuntimeError("mongo down"))

    result = svc.write(_req())

    assert result.status == WriteStatus.QUEUED
    assert queue.size == 1
    assert dead.size == 0

def test_mongo_upsert_insert_returns_inserted():
    idem = DummyIdempotency()
    mongo = FakeMongo(raw_upserted_id="raw_new_id", source_record_upserted_id="source_new_id")

    svc = NewsWriteService(
        idempotency=idem,
        queue=WriteQueue(10, 3),
        dead_letter=DeadLetterStore(),
        config=_cfg(),
        mongo_client=mongo,
        materializer=DummyMaterializer(),
    )

    result = svc.write(_req("https://example.com/new"))

    assert result.status == WriteStatus.INSERTED
    assert result.news_id == "source_new_id"
    assert mongo.raw_documents.last_upsert is True
    assert mongo.source_records.last_upsert is True
    assert mongo.raw_documents.last_filter["canonical_url"] == "https://example.com/new"

def test_mongo_upsert_existing_returns_duplicate_merged():
    idem = DummyIdempotency()
    mongo = FakeMongo(
        raw_existing_doc={
            "_id": "raw_existing_id",
            "canonical_url": "https://example.com/existing",
            "source_id": "source_doc_id",
            "title_raw": "Test haber",
            "text_raw": "icerik",
            "content_raw": "icerik",
            "published_at_raw": None,
            "scraped_at": "scraped_now",
            "updated_at": "updated_now",
        },
        source_record_existing_doc={"_id": "existing_id", "raw_document_id": "raw_existing_id"},
        raw_upserted_id=None,
        source_record_upserted_id=None,
    )

    svc = NewsWriteService(
        idempotency=idem,
        queue=WriteQueue(10, 3),
        dead_letter=DeadLetterStore(),
        config=_cfg(),
        mongo_client=mongo,
        materializer=DummyMaterializer(),
    )

    result = svc.write(_req("https://example.com/existing"))

    assert result.status == WriteStatus.DUPLICATE_MERGED
    assert result.news_id == "existing_id"
    assert result.was_duplicate is True
    assert mongo.raw_documents.last_upsert is True


def test_fail_closed_dead_letters_when_queue_full():
    idem = DummyIdempotency()
    queue = WriteQueue(0, 3)
    dead = DeadLetterStore()
    svc = NewsWriteService(
        idempotency=idem,
        queue=queue,
        dead_letter=dead,
        config=_cfg(),
        mongo_client="not-none",
        materializer=DummyMaterializer(),
    )

    svc._mongo_write = lambda request, idem_key: (_ for _ in ()).throw(RuntimeError("mongo down"))

    result = svc.write(_req())

    assert result.status == WriteStatus.DEAD_LETTERED
    assert queue.size == 0
    assert dead.size == 1
class FakeUpdateResult:
    def __init__(self, upserted_id=None):
        self.upserted_id = upserted_id


class FakeCollection:
    def __init__(self, existing_doc=None, upserted_id=None):
        self.existing_doc = existing_doc
        self.upserted_id = upserted_id
        self.last_filter = None
        self.last_update = None
        self.last_upsert = None

    def update_one(self, flt, update, upsert=False):
        self.last_filter = flt
        self.last_update = update
        self.last_upsert = upsert
        return FakeUpdateResult(upserted_id=self.upserted_id)

    def find_one(self, flt):
        if self.existing_doc is not None:
            return self.existing_doc
        doc = {}
        doc.update(self.last_update.get("$setOnInsert", {}))
        doc.update(self.last_update.get("$set", {}))
        doc["_id"] = self.upserted_id or "new_id"
        return doc


class FakeSourceCollection:
    def find_one(self, flt):
        return {
            "_id": "source_doc_id",
            "domain": flt["domain"],
            "display_name": "Example Source",
            "base_url": "https://example.com",
        }


class FakeInsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeInsertCollection:
    def __init__(self, inserted_id="crawl_session_id"):
        self.inserted_id = inserted_id
        self.last_doc = None

    def insert_one(self, doc):
        self.last_doc = doc
        return FakeInsertOneResult(self.inserted_id)


class FakeMongo:
    def __init__(
        self,
        raw_existing_doc=None,
        source_record_existing_doc=None,
        raw_upserted_id=None,
        source_record_upserted_id=None,
    ):
        self.sources = FakeSourceCollection()
        self.crawl_sessions = FakeInsertCollection()
        self.raw_documents = FakeCollection(existing_doc=raw_existing_doc, upserted_id=raw_upserted_id)
        self.source_records = FakeCollection(
            existing_doc=source_record_existing_doc,
            upserted_id=source_record_upserted_id,
        )

    def __getitem__(self, name):
        return {
            "sources": self.sources,
            "crawl_sessions": self.crawl_sessions,
            "raw_documents": self.raw_documents,
            "source_records": self.source_records,
        }
