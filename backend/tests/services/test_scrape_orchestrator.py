from app.services.scrape_orchestrator import (
    ScrapeTriggerResult,
    cleanup_refresh_data,
    discard_refresh_generation,
    has_scraped_news_data,
    start_bootstrap_scrape_if_needed,
    start_refresh_scrape,
)


class FakeCollection:
    def __init__(self, count: int):
        self.count = count
        self.count_calls: list[tuple[dict, int]] = []

    def count_documents(self, query: dict, limit: int = 0):
        self.count_calls.append((query, limit))
        return self.count


class FakeDatabase:
    def __init__(self, *, source_records_count: int = 0):
        self.collections = {
            "source_records": FakeCollection(source_records_count),
        }

    def __getitem__(self, name: str):
        return self.collections[name]


class FakeJobManager:
    def __init__(self):
        self.submitted: list[tuple[str | None, str]] = []

    def submit_job(self, source: str | None = None, trigger_type: str = "manual") -> str:
        self.submitted.append((source, trigger_type))
        return "job_123"


def test_has_scraped_news_data_returns_true_when_records_exist():
    database = FakeDatabase(source_records_count=1)

    result = has_scraped_news_data(database)

    assert result is True
    assert database.collections["source_records"].count_calls == [({}, 1)]


def test_start_bootstrap_scrape_if_needed_skips_when_data_exists():
    database = FakeDatabase(source_records_count=3)
    manager = FakeJobManager()

    result = start_bootstrap_scrape_if_needed(database, manager)

    assert result == ScrapeTriggerResult(
        status="already_initialized",
        trigger_type="bootstrap",
        reason="data_exists",
    )
    assert manager.submitted == []


def test_start_bootstrap_scrape_if_needed_submits_job_when_data_missing():
    database = FakeDatabase(source_records_count=0)
    manager = FakeJobManager()

    result = start_bootstrap_scrape_if_needed(database, manager)

    assert result == ScrapeTriggerResult(
        status="started",
        trigger_type="bootstrap",
        job_id="job_123",
    )
    assert manager.submitted == [(None, "bootstrap")]


def test_start_refresh_scrape_submits_job_without_reset():
    database = FakeDatabase(source_records_count=5)
    manager = FakeJobManager()

    result = start_refresh_scrape(database, manager)

    assert result == ScrapeTriggerResult(
        status="started",
        trigger_type="refresh",
        job_id="job_123",
    )
    assert manager.submitted == [(None, "refresh")]


def test_cleanup_refresh_data_delegates_to_cleanup_service(monkeypatch):
    database = FakeDatabase(source_records_count=0)
    fake_result = object()

    monkeypatch.setattr(
        "app.services.scrape_orchestrator.cleanup_stale_refresh_data",
        lambda db, active_generation: fake_result,
    )

    result = cleanup_refresh_data(database, active_generation="generation-live")

    assert result is fake_result


def test_discard_refresh_generation_delegates_to_cleanup_service(monkeypatch):
    database = FakeDatabase(source_records_count=0)
    fake_result = object()

    monkeypatch.setattr(
        "app.services.scrape_orchestrator.cleanup_pending_refresh_data",
        lambda db, pending_generation: fake_result,
    )

    result = discard_refresh_generation(database, pending_generation="generation-candidate")

    assert result is fake_result
