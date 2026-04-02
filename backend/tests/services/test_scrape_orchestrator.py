from app.services.scrape_orchestrator import (
    ScrapeTriggerResult,
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


def test_start_refresh_scrape_resets_then_submits_job(monkeypatch):
    database = FakeDatabase(source_records_count=5)
    manager = FakeJobManager()
    fake_reset_result = type(
        "FakeResetResult",
        (),
        {"deleted_counts": {"raw_documents": 5}, "total_deleted": 5},
    )()

    monkeypatch.setattr(
        "app.services.scrape_orchestrator.reset_scraped_news_data",
        lambda database: fake_reset_result,
    )

    result = start_refresh_scrape(database, manager)

    assert result == ScrapeTriggerResult(
        status="started",
        trigger_type="refresh",
        job_id="job_123",
        reset_result=fake_reset_result,
    )
    assert manager.submitted == [(None, "refresh")]
