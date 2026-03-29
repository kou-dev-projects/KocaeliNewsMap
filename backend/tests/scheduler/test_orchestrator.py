from app.scheduler.config import SchedulerConfig
from app.scheduler.orchestrator import (
    DynamicSourceDefinition,
    ScrapeOrchestrator,
    StaticSourceDefinition,
)


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


class FakeMCPServer:
    def __init__(self):
        self.calls = []

    def call(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        if tool_name == "acquire_lease":
            return {"acquired": True}
        if tool_name == "write_news":
            return {
                "status": "inserted",
                "news_id": "news_1",
                "was_duplicate": False,
                "reason": None,
            }
        if tool_name == "release_lease":
            return {"released": True}
        raise AssertionError(f"unexpected tool: {tool_name}")


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
            "published_at_raw": "2026-03-23T10:30:00+03:00",
            "image_url": "https://example.com/image.jpg",
        }


class FakeParser:
    def build_record(self, url, detail_data):
        return {
            "source_domain": "cagdaskocaeli.com.tr",
            "url": url,
            "title": detail_data["title"],
            "content_text": detail_data["content_text"],
            "published_at_raw": detail_data["published_at_raw"],
            "image_url": detail_data["image_url"],
            "scraped_at": "2026-03-23T08:00:00+00:00",
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
            "image_url": "",
        }

    def close(self):
        type(self).closed = True


class FakePlaywrightClient:
    stopped = False

    def __init__(self, *args, **kwargs):
        pass

    async def stop(self):
        type(self).stopped = True


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

    orchestrator = ScrapeOrchestrator(
        config=SchedulerConfig(
            enabled=True,
            timezone="Europe/Istanbul",
            interval_hours=3,
            lookback_days=1,
            max_urls_per_source=1,
        ),
        database=FakeDatabase(source_docs),
        mcp_server=FakeMCPServer(),
        session_store=FakeSessionStore(),
    )

    summary = orchestrator.crawl_active_sources(trigger_type="scheduled")

    assert summary["active_sources"] == 2
    assert summary["processed_sources"] == 1
    assert summary["skipped_sources"] == 1
    assert summary["sessions"][0]["status"] == "success"
    assert summary["sessions"][0]["parsed_count"] == 1
    tool_names = [name for name, _ in orchestrator._mcp.calls]
    assert tool_names == ["acquire_lease", "write_news", "release_lease"]
    write_kwargs = orchestrator._mcp.calls[1][1]
    assert write_kwargs["crawl_session_id"] == "session_1"
    assert write_kwargs["parser_version"] == "FakeParser"


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

    orchestrator = ScrapeOrchestrator(
        config=SchedulerConfig(
            enabled=True,
            timezone="Europe/Istanbul",
            interval_hours=3,
            lookback_days=1,
            max_urls_per_source=1,
        ),
        database=FakeDatabase(source_docs),
        mcp_server=FakeMCPServer(),
        session_store=FakeSessionStore(),
    )

    def fake_crawl_single_source(*, source_document, trigger_type):
        assert trigger_type == "scheduled"
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


def test_crawl_source_returns_skipped_for_unsupported_source():
    source_docs = [
        {
            "_id": "source_2",
            "domain": "unsupported.example.com",
            "base_url": "https://unsupported.example.com",
            "scraper_type": "static",
        }
    ]

    orchestrator = ScrapeOrchestrator(
        config=SchedulerConfig(
            enabled=True,
            timezone="Europe/Istanbul",
            interval_hours=3,
            lookback_days=1,
            max_urls_per_source=1,
        ),
        database=FakeDatabase(source_docs),
        mcp_server=FakeMCPServer(),
        session_store=FakeSessionStore(),
    )

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

    fake_mcp = FakeMCPServer()
    session_store = StatusAwareSessionStore()
    orchestrator = ScrapeOrchestrator(
        config=SchedulerConfig(
            enabled=True,
            timezone="Europe/Istanbul",
            interval_hours=3,
            lookback_days=1,
            max_urls_per_source=1,
        ),
        database=FakeDatabase(source_docs),
        mcp_server=fake_mcp,
        session_store=session_store,
    )

    result = orchestrator.crawl_source("cagdaskocaeli.com.tr", trigger_type="manual")

    assert result["status"] == "failed"
    assert result["failed_count"] == 1
    assert session_store.finalized[0]["failed_count"] == 1
    assert session_store.finalized[0]["error_summary"][0]["code"] == "source_bootstrap_error"
    tool_names = [name for name, _ in fake_mcp.calls]
    assert tool_names == ["acquire_lease", "release_lease"]


def test_crawl_source_returns_skipped_for_configured_domain():
    source_docs = [
        {
            "_id": "source_3",
            "domain": "yenikocaeli.com",
            "base_url": "https://www.yenikocaeli.com",
            "scraper_type": "static",
        }
    ]

    fake_mcp = FakeMCPServer()
    orchestrator = ScrapeOrchestrator(
        config=SchedulerConfig(
            enabled=True,
            timezone="Europe/Istanbul",
            interval_hours=3,
            lookback_days=1,
            max_urls_per_source=1,
            skipped_domains=("yenikocaeli.com",),
        ),
        database=FakeDatabase(source_docs),
        mcp_server=fake_mcp,
        session_store=FakeSessionStore(),
    )

    result = orchestrator.crawl_source("yenikocaeli.com", trigger_type="manual")

    assert result == {
        "domain": "yenikocaeli.com",
        "status": "skipped",
        "reason": "skipped_by_config",
    }
    assert fake_mcp.calls == []


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

    orchestrator = ScrapeOrchestrator(
        config=SchedulerConfig(
            enabled=True,
            timezone="Europe/Istanbul",
            interval_hours=3,
            lookback_days=1,
            max_urls_per_source=1,
        ),
        database=FakeDatabase(source_docs),
        mcp_server=FakeMCPServer(),
        session_store=FakeSessionStore(),
    )

    result = orchestrator.crawl_source("dynamic.example.com", trigger_type="manual")

    assert result["status"] == "success"
    assert FakeDynamicListingScraper.closed is True
    assert FakeDynamicDetailScraper.closed is True
    assert FakePlaywrightClient.stopped is True
