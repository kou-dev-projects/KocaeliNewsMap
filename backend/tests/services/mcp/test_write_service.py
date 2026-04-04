
from app.services.mcp.config import MCPConfig
from app.services.mcp.dead_letter import DeadLetterStore
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
            "summary": raw_document["content_raw"] or raw_document["text_raw"],
            "published_at": raw_document["published_at_raw"] or raw_document["scraped_at"],
            "category_predicted": "unknown",
            "category_confidence": 0.0,
            "district_predicted": None,
            "location_text_extracted": None,
            "geocode_status": "not_needed",
            "dedupe_hash": "dedupe-test-hash",
            "kaynak_listesi": [raw_document["domain"]],
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
        worker_id="test-worker",
    )


def _req(
    url: str = "https://example.com/a",
    *,
    source: str = "example.com",
    title: str = "Test haber",
    content: str = "icerik",
) -> NewsWriteRequest:
    return NewsWriteRequest(
        title=title,
        url=url,
        source=source,
        content=content,
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


def test_duplicate_still_refreshes_existing_record():
    idem = DummyIdempotency()
    req = _req("https://example.com/existing-refresh")
    idem_key = req.idempotency_key()
    idem.mark_processed(idem_key, "news_123")
    mongo = FakeMongo(
        raw_existing_doc={
            "_id": "raw_existing_id",
            "canonical_url": "https://example.com/existing-refresh",
            "source_id": "source_example.com",
            "title_raw": "Test haber",
            "text_raw": "icerik",
            "content_raw": "icerik",
            "published_at_raw": None,
            "scraped_at": "scraped_now",
            "updated_at": "updated_now",
        },
        source_record_existing_doc={"_id": "news_123", "raw_document_id": "raw_existing_id"},
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

    result = svc.write(req)

    assert result.status == WriteStatus.DUPLICATE_MERGED
    assert result.news_id == "news_123"
    assert result.was_duplicate is True
    assert mongo.raw_documents.last_filter["canonical_url"] == "https://example.com/existing-refresh"


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


def test_process_queue_batch_processes_items_successfully():
    idem = DummyIdempotency()
    queue = WriteQueue(10, 3)
    dead = DeadLetterStore()
    request = _req("https://example.com/queued-success")
    queue.enqueue(request)

    svc = NewsWriteService(
        idempotency=idem,
        queue=queue,
        dead_letter=dead,
        config=_cfg(),
        mongo_client=None,
        materializer=DummyMaterializer(),
    )

    summary = svc.process_queue_batch(batch_size=10)

    assert summary == {
        "dequeued": 1,
        "processed": 1,
        "requeued": 0,
        "dead_lettered": 0,
    }
    assert queue.size == 0
    assert idem.is_duplicate(request.idempotency_key()) is True


def test_process_queue_batch_duplicate_still_rewrites_existing_record():
    idem = DummyIdempotency()
    request = _req("https://example.com/queued-duplicate")
    idem.mark_processed(request.idempotency_key(), "existing_news")
    queue = WriteQueue(10, 3)
    dead = DeadLetterStore()
    queue.enqueue(request)
    mongo = FakeMongo(
        raw_existing_doc={
            "_id": "raw_existing_id",
            "canonical_url": "https://example.com/queued-duplicate",
            "source_id": "source_example.com",
            "title_raw": "Test haber",
            "text_raw": "icerik",
            "content_raw": "icerik",
            "published_at_raw": None,
            "scraped_at": "scraped_now",
            "updated_at": "updated_now",
        },
        source_record_existing_doc={"_id": "existing_news", "raw_document_id": "raw_existing_id"},
        raw_upserted_id=None,
        source_record_upserted_id=None,
    )

    svc = NewsWriteService(
        idempotency=idem,
        queue=queue,
        dead_letter=dead,
        config=_cfg(),
        mongo_client=mongo,
        materializer=DummyMaterializer(),
    )

    summary = svc.process_queue_batch(batch_size=10)

    assert summary == {
        "dequeued": 1,
        "processed": 1,
        "requeued": 0,
        "dead_lettered": 0,
    }
    assert queue.size == 0
    assert mongo.raw_documents.last_filter["canonical_url"] == "https://example.com/queued-duplicate"


def test_process_queue_batch_requeues_when_write_still_fails():
    idem = DummyIdempotency()
    queue = WriteQueue(10, 3)
    dead = DeadLetterStore()
    queue.enqueue(_req("https://example.com/queued-retry"))

    svc = NewsWriteService(
        idempotency=idem,
        queue=queue,
        dead_letter=dead,
        config=_cfg(),
        mongo_client="not-none",
        materializer=DummyMaterializer(),
    )
    svc._mongo_write = lambda request, idem_key: (_ for _ in ()).throw(RuntimeError("mongo down"))

    summary = svc.process_queue_batch(batch_size=10)

    assert summary == {
        "dequeued": 1,
        "processed": 0,
        "requeued": 1,
        "dead_lettered": 0,
    }
    assert queue.size == 1
    requeued_item = queue.dequeue_batch(1)[0]
    assert requeued_item.attempt_count == 1


def test_process_queue_batch_dead_letters_when_max_retry_reached():
    idem = DummyIdempotency()
    queue = WriteQueue(10, 0)
    dead = DeadLetterStore()
    queue.enqueue(_req("https://example.com/queued-dead-letter"))

    svc = NewsWriteService(
        idempotency=idem,
        queue=queue,
        dead_letter=dead,
        config=_cfg(),
        mongo_client="not-none",
        materializer=DummyMaterializer(),
    )
    svc._mongo_write = lambda request, idem_key: (_ for _ in ()).throw(RuntimeError("mongo down"))

    summary = svc.process_queue_batch(batch_size=10)

    assert summary == {
        "dequeued": 1,
        "processed": 0,
        "requeued": 0,
        "dead_lettered": 1,
    }
    assert queue.size == 0
    assert dead.size == 1

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
            "source_id": "source_example.com",
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


def test_cross_source_duplicate_merges_into_existing_canonical():
    idem = DummyIdempotency()
    mongo = FakeMongo(
        duplicate_source_record_doc={
            "_id": "canonical_id",
            "raw_document_id": "raw_canonical_id",
            "dedupe_hash": "dedupe-test-hash",
            "record_status": "active",
            "kaynak_listesi": ["bizimyaka.com.tr"],
            "category_predicted": "unknown",
            "category_confidence": 0.0,
            "geocode_status": "not_needed",
            "updated_at": "old_time",
        },
        raw_upserted_id="raw_new_id",
        source_record_upserted_id="source_new_id",
    )

    svc = NewsWriteService(
        idempotency=idem,
        queue=WriteQueue(10, 3),
        dead_letter=DeadLetterStore(),
        config=_cfg(),
        mongo_client=mongo,
        materializer=DummyMaterializer(),
    )

    result = svc.write(
        _req(
            "https://other.example.com/haber",
            source="ozgurkocaeli.com.tr",
        )
    )

    assert result.status == WriteStatus.DUPLICATE_MERGED
    assert result.news_id == "canonical_id"
    assert result.was_duplicate is True

    canonical_doc = mongo.source_records.find_one({"_id": "canonical_id"})
    merged_doc = mongo.source_records.find_one({"raw_document_id": "raw_new_id"})
    assert canonical_doc["kaynak_listesi"] == [
        "bizimyaka.com.tr",
        "ozgurkocaeli.com.tr",
    ]
    assert merged_doc["record_status"] == "merged_duplicate"
    assert merged_doc["duplicate_of_record_id"] == "canonical_id"


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


def test_relative_image_url_is_normalized_for_raw_document():
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

    request = NewsWriteRequest(
        title="Test haber",
        url="https://example.com/haber/1",
        source="example.com",
        content="icerik",
        image_url="/images/test.jpg",
    )

    svc.write(request)

    assert mongo.raw_documents.last_update["$set"]["image_urls_raw"] == [
        "https://example.com/images/test.jpg"
    ]


def test_invalid_image_url_is_dropped_from_raw_document():
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

    request = NewsWriteRequest(
        title="Test haber",
        url="https://example.com/haber/1",
        source="example.com",
        content="icerik",
        image_url="javascript:alert(1)",
    )

    svc.write(request)

    assert mongo.raw_documents.last_update["$set"]["image_urls_raw"] == []


def test_dataset_generation_is_written_to_raw_and_source_records():
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

    request = NewsWriteRequest(
        title="Snapshot write",
        url="https://example.com/snapshot",
        source="example.com",
        content="icerik",
        dataset_generation="generation-42",
    )

    svc.write(request)

    assert mongo.raw_documents.last_filter["dataset_generation"] == "generation-42"
    assert mongo.raw_documents.last_update["$set"]["dataset_generation"] == "generation-42"
    assert mongo.source_records.last_update["$set"]["dataset_generation"] == "generation-42"


class FakeUpdateResult:
    def __init__(self, upserted_id=None):
        self.upserted_id = upserted_id


class FakeCollection:
    def __init__(self, docs=None, upserted_id=None):
        self.docs = [dict(doc) for doc in (docs or [])]
        self.upserted_id = upserted_id
        self.last_filter = None
        self.last_update = None
        self.last_upsert = None

    def _matches(self, doc, flt):
        for key, expected in flt.items():
            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$ne" in expected and actual == expected["$ne"]:
                    return False
                continue
            if actual != expected:
                return False
        return True

    def update_one(self, flt, update, upsert=False):
        self.last_filter = flt
        self.last_update = update
        self.last_upsert = upsert
        for doc in self.docs:
            if self._matches(doc, flt):
                doc.update(update.get("$set", {}))
                return FakeUpdateResult(upserted_id=None)

        if not upsert:
            return FakeUpdateResult(upserted_id=None)

        doc = {
            key: value
            for key, value in flt.items()
            if not isinstance(value, dict)
        }
        doc.update(update.get("$setOnInsert", {}))
        doc.update(update.get("$set", {}))
        doc["_id"] = self.upserted_id or doc.get("_id") or "new_id"
        self.docs.append(doc)
        return FakeUpdateResult(upserted_id=doc["_id"])

    def find_one(self, flt):
        for doc in self.docs:
            if self._matches(doc, flt):
                return dict(doc)
        return None


class FakeSourceCollection:
    def find_one(self, flt):
        return {
            "_id": f"source_{flt['domain']}",
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
        duplicate_source_record_doc=None,
        raw_upserted_id=None,
        source_record_upserted_id=None,
    ):
        self.sources = FakeSourceCollection()
        self.crawl_sessions = FakeInsertCollection()
        raw_docs = [raw_existing_doc] if raw_existing_doc is not None else []
        source_record_docs = []
        if source_record_existing_doc is not None:
            source_record_docs.append(source_record_existing_doc)
        if duplicate_source_record_doc is not None:
            source_record_docs.append(duplicate_source_record_doc)
        self.raw_documents = FakeCollection(docs=raw_docs, upserted_id=raw_upserted_id)
        self.source_records = FakeCollection(
            docs=source_record_docs,
            upserted_id=source_record_upserted_id,
        )

    def __getitem__(self, name):
        return {
            "sources": self.sources,
            "crawl_sessions": self.crawl_sessions,
            "raw_documents": self.raw_documents,
            "source_records": self.source_records,
        }
