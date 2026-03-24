from datetime import datetime, timezone

from app.scheduler.sessions import CrawlSessionStore


class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeCollection:
    def __init__(self):
        self.inserted = []
        self.updated = []

    def insert_one(self, document):
        self.inserted.append(document)
        return FakeInsertResult("session_1")

    def update_one(self, flt, update):
        self.updated.append((flt, update))


class FakeDatabase:
    def __init__(self):
        self.collections = {
            "crawl_sessions": FakeCollection(),
        }

    def __getitem__(self, name):
        return self.collections[name]


def test_create_for_source_inserts_running_session():
    database = FakeDatabase()
    store = CrawlSessionStore(database)

    session_id = store.create_for_source(
        source_id="source_1",
        trigger_type="scheduled",
        lookback_days=2,
        worker_version="scheduler_v1",
        trace_id="trace1234",
    )

    assert session_id == "session_1"
    inserted = database["crawl_sessions"].inserted[0]
    assert inserted["status"] == "running"
    assert inserted["scope"] == "single_source"
    assert inserted["lookback_days"] == 2
    assert inserted["trace_id"] == "trace1234"
    assert isinstance(inserted["started_at"], datetime)
    assert inserted["started_at"].tzinfo == timezone.utc


def test_finalize_marks_partial_when_some_records_fail():
    database = FakeDatabase()
    store = CrawlSessionStore(database)

    status = store.finalize(
        session_id="session_1",
        fetched_count=3,
        parsed_count=2,
        failed_count=1,
        error_summary=[{"code": "detail_error", "message": "boom"}],
    )

    assert status == "partial"
    flt, update = database["crawl_sessions"].updated[0]
    assert flt == {"_id": "session_1"}
    assert update["$set"]["status"] == "partial"
    assert update["$set"]["fetched_count"] == 3
    assert update["$set"]["parsed_count"] == 2
    assert update["$set"]["failed_count"] == 1
