from datetime import datetime, timedelta, timezone

from app.scheduler.config import SchedulerConfig
from app.scheduler.orchestrator import (
    DynamicSourceDefinition,
    ScrapeOrchestrator,
    StaticSourceDefinition,
)
from app.services.mcp.schemas import WriteResult, WriteStatus


class FakeSourcesCollection:
    def __init__(self, docs):
        self._docs = docs

    def find(self, flt, projection):
        assert flt == {"active": True}
        return list(self._docs)

    def find_one(self, flt, projection):
        for doc in self._docs:
            if doc["domain"] == flt["domain"] and flt["active"] is True:
                return doc
        return None


class FakeDatabase:
    def __init__(self, source_docs):
        self._sources = FakeSourcesCollection(source_docs)

    def __getitem__(self, name):
        if name == "sources":
            return self._sources
        raise KeyError(name)


class FakeWriteService:

    def __init__(self):
        self.calls = []

    def write(self, request):
        self.calls.append(request)
        return WriteResult(
            status=WriteStatus.INSERTED,
            news_id="news_1",
            was_duplicate=False,
            idempotency_key="fake_key",
        )

    def process_queue_batch(self, *, batch_size=20):
        return {"dequeued": 0, "processed": 0, "requeued": 0, "dead_lettered": 0}


class FakeLease:

    def __init__(self):
        self.acquired = []
        self.released = []

    def acquire(self, source, worker_id):
        self.acquired.append((source, worker_id))
        return True

    def release(self, source, worker_id):
        self.released.append((source, worker_id))
        return True


class FakeSessionStore:
    def __init__(self):
        self.created = []
        self.finalized = []

    def create_for_source(self, **kwargs):
        self.created.append(kwargs)
        return "session_1"

    def finalize(self, **kwargs):
        self.finalized.append(kwargs)
        return "success"


class StatusAwareSessionStore(FakeSessionStore):
    def finalize(self, **kwargs):
        self.finalized.append(kwargs)
        if kwargs["failed_count"] > 0:
            return "failed"
        return "success"


class FakeListingScraper:
    def fetch_listing_html(self, url):
        return "<html></html>"

    def extract_news_urls(self, html):
        return [
            "https://example.com/news-1",
            "https://example.com/news-2",
        ]


class FakeDetailScraper:
    def fetch_detail_html(self, url):
        return "<html></html>"

    def extract_detail_fields(self, html):
        return {
            "title": "Test baslik",
            "content_text": "Test icerik",
            "published_at_raw": datetime.now(timezone.utc).isoformat(),
        }


class FakeParser:
    def build_record(self, url, detail_data):
        return {
            "source_domain": "cagdaskocaeli.com.tr",
            "url": url,
            "title": detail_data["title"],
            "content_text": detail_data["content_text"],
            "published_at_raw": detail_data["published_at_raw"],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }


class FakeDynamicListingScraper:
    closed = False

    def __init__(self, client, listing_url):
        self.client = client

    async def fetch_links(self):
        return ["https://example.com/news-dynamic"]

    def close(self):
        type(self).closed = True


class FakeDynamicDetailScraper:
    closed = False

    def __init__(self, client):
        self.client = client

    async def fetch_detail(self, url):
        return {
            "title": "Dynamic baslik",
            "content": "Dynamic icerik",
            "summary": "",
            "published_at_raw": "",
        }

    def close(self):
        type(self).closed = True


class FakePlaywrightClient:
    stopped = False

    def __init__(self, *args, **kwargs):
        pass

    async def stop(self):
        type(self).stopped = True


def _make_orchestrator(source_docs, write_service=None, lease=None, session_store=None, config=None):
    return ScrapeOrchestrator(
        config=config or SchedulerConfig(
            enabled=True,
            timezone="Europe/Istanbul",
            interval_hours=3,
            lookback_days=1,
            max_urls_per_source=1,
        ),
        database=FakeDatabase(source_docs),
        write_service=write_service or FakeWriteService(),
        lease=lease or FakeLease(),
        session_store=session_store or FakeSessionStore(),
    )


def test_crawl_active_sources_processes_supported_sources(monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.orchestrator.STATIC_SOURCE_REGISTRY",
        {
            "cagdaskocaeli.com.tr": StaticSourceDefinition(
                listing_scraper_factory=FakeListingScraper,
                detail_scraper_factory=FakeDetailScraper,
                parser_factory=FakeParser,
            )
        },
    )
    monkeypatch.setattr("app.scheduler.orchestrator.DYNAMIC_SOURCE_REGISTRY", {})

    source_docs = [
        {
            "_id": "source_1",
            "domain": "cagdaskocaeli.com.tr",
            "base_url": "https://www.cagdaskocaeli.com.tr",
            "scraper_type": "static",
        },
        {
            "_id": "source_2",
            "domain": "seskocaeli.com",
            "base_url": "https://www.seskocaeli.com",
            "scraper_type": "dynamic",
        },
    ]

    write_service = FakeWriteService()
    lease = FakeLease()
    orchestrator = _make_orchestrator(
        source_docs,
        write_service=write_service,
        lease=lease,
    )

    summary = orchestrator.crawl_active_sources(trigger_type="scheduled")

    assert summary["active_sources"] == 2
    assert summary["processed_sources"] == 1
    assert summary["skipped_sources"] == 1
    assert summary["skipped_session_reasons"] == ["unsupported_source"]
    assert summary["sessions"][0]["status"] == "success"
    assert summary["sessions"][0]["parsed_count"] == 1
    # Verify lease was acquired and released
    assert len(lease.acquired) == 1
    assert len(lease.released) == 1
    # Verify write service was called
    assert len(write_service.calls) == 1
    assert write_service.calls[0].parser_version == "FakeParser"
    assert write_service.calls[0].crawl_session_id == "session_1"


def test_crawl_active_sources_continues_when_single_source_raises(monkeypatch):
    source_docs = [
        {
            "_id": "source_1",
            "domain": "broken.example.com",
            "base_url": "https://broken.example.com",
            "scraper_type": "static",
        },
        {
            "_id": "source_2",
            "domain": "ok.example.com",
            "base_url": "https://ok.example.com",
            "scraper_type": "static",
        },
    ]

    orchestrator = _make_orchestrator(source_docs)

    def fake_crawl_single_source(
        *,
        source_document,
        trigger_type,
        dataset_generation=None,
        progress_callback=None,
        should_cancel=None,
    ):
        assert trigger_type == "scheduled"
        assert dataset_generation is None
        assert progress_callback is None
        assert should_cancel is None
        if source_document["domain"] == "broken.example.com":
            raise RuntimeError("boom")
        return {
            "domain": "ok.example.com",
            "status": "success",
            "session_id": "session_ok",
            "fetched_count": 1,
            "parsed_count": 1,
            "failed_count": 0,
        }

    monkeypatch.setattr(orchestrator, "_crawl_single_source", fake_crawl_single_source)

    summary = orchestrator.crawl_active_sources(trigger_type="scheduled")

    assert summary["active_sources"] == 2
    assert summary["processed_sources"] == 2
    assert summary["skipped_sources"] == 0
    assert len(summary["sessions"]) == 2
    failed_session = next(item for item in summary["sessions"] if item["domain"] == "broken.example.com")
    assert failed_session["status"] == "failed"
    assert failed_session["reason"] == "unhandled_source_exception"
    assert failed_session["error_type"] == "RuntimeError"
    assert failed_session["error_message"] == "boom"
    assert summary["failed_sources"] == 1
    assert summary["status"] == "completed_with_errors"


def test_crawl_active_sources_marks_failed_when_all_processed_sources_fail(monkeypatch):
    source_docs = [
        {
            "_id": "source_1",
            "domain": "broken-a.example.com",
            "base_url": "https://broken-a.example.com",
            "scraper_type": "static",
        },
        {
            "_id": "source_2",
            "domain": "broken-b.example.com",
            "base_url": "https://broken-b.example.com",
            "scraper_type": "static",
        },
    ]

    orchestrator = _make_orchestrator(source_docs)

    def fake_crawl_single_source(
        *,
        source_document,
        trigger_type,
        dataset_generation=None,
        progress_callback=None,
        should_cancel=None,
    ):
        return {
            "domain": source_document["domain"],
            "status": "failed",
            "failed_count": 1,
        }

    monkeypatch.setattr(orchestrator, "_crawl_single_source", fake_crawl_single_source)

    summary = orchestrator.crawl_active_sources(trigger_type="scheduled")

    assert summary["processed_sources"] == 2
    assert summary["failed_sources"] == 2
    assert summary["status"] == "failed"


def test_crawl_source_returns_skipped_for_unsupported_source():
    source_docs = [
        {
            "_id": "source_2",
            "domain": "unsupported.example.com",
            "base_url": "https://unsupported.example.com",
            "scraper_type": "static",
        }
    ]

    orchestrator = _make_orchestrator(source_docs)

    result = orchestrator.crawl_source("unsupported.example.com", trigger_type="manual")

    assert result == {
        "domain": "unsupported.example.com",
        "status": "skipped",
        "reason": "unsupported_source",
    }


def test_crawl_source_static_bootstrap_failure_releases_lease(monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.orchestrator.STATIC_SOURCE_REGISTRY",
        {
            "cagdaskocaeli.com.tr": StaticSourceDefinition(
                listing_scraper_factory=lambda: (_ for _ in ()).throw(RuntimeError("factory_error")),
                detail_scraper_factory=FakeDetailScraper,
                parser_factory=FakeParser,
            )
        },
    )
    monkeypatch.setattr("app.scheduler.orchestrator.DYNAMIC_SOURCE_REGISTRY", {})

    source_docs = [
        {
            "_id": "source_1",
            "domain": "cagdaskocaeli.com.tr",
            "base_url": "https://www.cagdaskocaeli.com.tr",
            "scraper_type": "static",
        }
    ]

    lease = FakeLease()
    session_store = StatusAwareSessionStore()
    orchestrator = _make_orchestrator(
        source_docs,
        lease=lease,
        session_store=session_store,
    )

    result = orchestrator.crawl_source("cagdaskocaeli.com.tr", trigger_type="manual")

    assert result["status"] == "failed"
    assert result["failed_count"] == 1
    assert result["error_type"] == "RuntimeError"
    assert "factory_error" in result["error_message"]
    assert session_store.finalized[0]["failed_count"] == 1
    assert session_store.finalized[0]["error_summary"][0]["code"] == "source_bootstrap_error"
    assert session_store.finalized[0]["error_summary"][0]["error_type"] == "RuntimeError"
    # Verify lease was acquired then released
    assert len(lease.acquired) == 1
    assert len(lease.released) == 1


def test_crawl_source_returns_skipped_for_configured_domain():
    source_docs = [
        {
            "_id": "source_3",
            "domain": "yenikocaeli.com",
            "base_url": "https://www.yenikocaeli.com",
            "scraper_type": "static",
        }
    ]

    lease = FakeLease()
    orchestrator = _make_orchestrator(
        source_docs,
        lease=lease,
        config=SchedulerConfig(
            enabled=True,
            timezone="Europe/Istanbul",
            interval_hours=3,
            lookback_days=1,
            max_urls_per_source=1,
            skipped_domains=("yenikocaeli.com",),
        ),
    )

    result = orchestrator.crawl_source("yenikocaeli.com", trigger_type="manual")

    assert result == {
        "domain": "yenikocaeli.com",
        "status": "skipped",
        "reason": "skipped_by_config",
    }
    # Lease should not be acquired for skipped domains
    assert lease.acquired == []


def test_crawl_source_dynamic_closes_scrapers(monkeypatch):
    FakeDynamicListingScraper.closed = False
    FakeDynamicDetailScraper.closed = False
    FakePlaywrightClient.stopped = False

    monkeypatch.setattr("app.scheduler.orchestrator.STATIC_SOURCE_REGISTRY", {})
    monkeypatch.setattr(
        "app.scheduler.orchestrator.DYNAMIC_SOURCE_REGISTRY",
        {
            "dynamic.example.com": DynamicSourceDefinition(
                listing_scraper_factory=lambda client, base_url: FakeDynamicListingScraper(client, base_url),
                detail_scraper_factory=lambda client: FakeDynamicDetailScraper(client),
            )
        },
    )
    monkeypatch.setattr("app.scheduler.orchestrator.PlaywrightClient", FakePlaywrightClient)

    source_docs = [
        {
            "_id": "source_dynamic",
            "domain": "dynamic.example.com",
            "base_url": "https://dynamic.example.com",
            "scraper_type": "dynamic",
        }
    ]

    orchestrator = _make_orchestrator(source_docs)

    result = orchestrator.crawl_source("dynamic.example.com", trigger_type="manual")

    assert result["status"] == "success"
    assert FakeDynamicListingScraper.closed is True
    assert FakeDynamicDetailScraper.closed is True
    assert FakePlaywrightClient.stopped is True


def test_crawl_source_static_processing_failure_exposes_error_details(monkeypatch):
    class BrokenDetailScraper(FakeDetailScraper):
        def fetch_detail_html(self, url):
            raise ValueError("detail_boom")

    monkeypatch.setattr(
        "app.scheduler.orchestrator.STATIC_SOURCE_REGISTRY",
        {
            "cagdaskocaeli.com.tr": StaticSourceDefinition(
                listing_scraper_factory=FakeListingScraper,
                detail_scraper_factory=BrokenDetailScraper,
                parser_factory=FakeParser,
            )
        },
    )
    monkeypatch.setattr("app.scheduler.orchestrator.DYNAMIC_SOURCE_REGISTRY", {})

    source_docs = [
        {
            "_id": "source_1",
            "domain": "cagdaskocaeli.com.tr",
            "base_url": "https://www.cagdaskocaeli.com.tr",
            "scraper_type": "static",
        }
    ]

    session_store = StatusAwareSessionStore()
    orchestrator = _make_orchestrator(
        source_docs,
        session_store=session_store,
        config=SchedulerConfig(
            enabled=True,
            timezone="Europe/Istanbul",
            interval_hours=3,
            lookback_days=1,
            max_urls_per_source=1,
        ),
    )

    result = orchestrator.crawl_source("cagdaskocaeli.com.tr", trigger_type="manual")

    assert result["status"] == "failed"
    assert result["error_type"] == "ValueError"
    assert "detail_boom" in result["error_message"]
    error_summary = session_store.finalized[0]["error_summary"]
    assert error_summary[0]["code"] == "source_processing_error"
    assert error_summary[0]["error_type"] == "ValueError"


def test_crawl_source_emits_progress_events(monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.orchestrator.STATIC_SOURCE_REGISTRY",
        {
            "cagdaskocaeli.com.tr": StaticSourceDefinition(
                listing_scraper_factory=FakeListingScraper,
                detail_scraper_factory=FakeDetailScraper,
                parser_factory=FakeParser,
            )
        },
    )
    monkeypatch.setattr("app.scheduler.orchestrator.DYNAMIC_SOURCE_REGISTRY", {})

    source_docs = [
        {
            "_id": "source_1",
            "domain": "cagdaskocaeli.com.tr",
            "base_url": "https://www.cagdaskocaeli.com.tr",
            "scraper_type": "static",
            "display_name": "Cagdas Kocaeli",
        }
    ]

    orchestrator = _make_orchestrator(source_docs)
    events = []

    result = orchestrator.crawl_source(
        "cagdaskocaeli.com.tr",
        trigger_type="manual",
        progress_callback=events.append,
    )

    assert result["status"] == "success"
    assert [event["event"] for event in events] == [
        "source_crawl_started",
        "source_listing_collected",
        "source_progress_checkpoint",
        "source_crawl_completed",
    ]
    assert events[1]["details"]["listing_count"] == 1
    assert events[1]["details"]["sample_url"] == "https://example.com/news-1"
    assert events[2]["details"]["url_index"] == 1
    assert events[2]["details"]["total_urls"] == 1
    assert events[2]["details"]["outcome"] == "inserted"
    assert events[2]["details"]["parsed_count"] == 1
    assert events[3]["details"]["parsed_count"] == 1


def test_crawl_source_skips_records_older_than_lookback(monkeypatch):
    class OldDetailScraper(FakeDetailScraper):
        def extract_detail_fields(self, html):
            return {
                "title": "Eski haber",
                "content_text": "Eski icerik",
                "published_at_raw": (datetime.now(timezone.utc) - timedelta(days=4)).isoformat(),
            }

    monkeypatch.setattr(
        "app.scheduler.orchestrator.STATIC_SOURCE_REGISTRY",
        {
            "cagdaskocaeli.com.tr": StaticSourceDefinition(
                listing_scraper_factory=FakeListingScraper,
                detail_scraper_factory=OldDetailScraper,
                parser_factory=FakeParser,
            )
        },
    )
    monkeypatch.setattr("app.scheduler.orchestrator.DYNAMIC_SOURCE_REGISTRY", {})

    source_docs = [
        {
            "_id": "source_1",
            "domain": "cagdaskocaeli.com.tr",
            "base_url": "https://www.cagdaskocaeli.com.tr",
            "scraper_type": "static",
        }
    ]

    write_service = FakeWriteService()
    orchestrator = _make_orchestrator(
        source_docs,
        write_service=write_service,
        config=SchedulerConfig(
            enabled=True,
            timezone="Europe/Istanbul",
            interval_hours=3,
            lookback_days=3,
            max_urls_per_source=1,
        ),
    )

    result = orchestrator.crawl_source("cagdaskocaeli.com.tr", trigger_type="manual")

    assert result["status"] == "success"
    assert result["fetched_count"] == 1
    assert result["parsed_count"] == 0
    assert result["failed_count"] == 0
    assert write_service.calls == []
