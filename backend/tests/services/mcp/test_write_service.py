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
    )

    svc._mongo_write = lambda request, idem_key: (_ for _ in ()).throw(RuntimeError("mongo down"))

    result = svc.write(_req())

    assert result.status == WriteStatus.QUEUED
    assert queue.size == 1
    assert dead.size == 0

def test_mongo_upsert_insert_returns_inserted():
    idem = DummyIdempotency()
    collection = FakeCollection(upserted_id="new_id")
    mongo = FakeMongo(collection)

    svc = NewsWriteService(
        idempotency=idem,
        queue=WriteQueue(10, 3),
        dead_letter=DeadLetterStore(),
        config=_cfg(),
        mongo_client=mongo,
    )

    result = svc.write(_req("https://example.com/new"))

    assert result.status == WriteStatus.INSERTED
    assert result.news_id == "new_id"
    assert collection.last_upsert is True
    assert collection.last_filter == {"url": "https://example.com/new"}

def test_mongo_upsert_existing_returns_duplicate_merged():
    idem = DummyIdempotency()
    collection = FakeCollection(
        existing_doc={"_id": "existing_id", "url": "https://example.com/existing"},
        upserted_id=None,
    )
    mongo = FakeMongo(collection)

    svc = NewsWriteService(
        idempotency=idem,
        queue=WriteQueue(10, 3),
        dead_letter=DeadLetterStore(),
        config=_cfg(),
        mongo_client=mongo,
    )

    result = svc.write(_req("https://example.com/existing"))

    assert result.status == WriteStatus.DUPLICATE_MERGED
    assert result.news_id == "existing_id"
    assert result.was_duplicate is True
    assert collection.last_upsert is True


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
        return {"_id": self.upserted_id or "new_id", "url": flt["url"]}


class FakeMongo:
    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, name):
        return {"haberler": self.collection}
