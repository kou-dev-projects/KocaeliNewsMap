import time

import pytest

from app.services.dataset_generation import DatasetGenerationState
from app.scheduler.orchestrator import ScrapeCancellationRequested
from app.workers.job_manager import JobInfo
from app.workers.job_worker import (
    _collect_refresh_success,
    _execute_job_with_heartbeat,
    _is_retryable_error,
    _run_scrape_job,
)


class FakeJobManager:
    def __init__(self):
        self.heartbeat_calls = 0
        self.cancel_requested = False

    def heartbeat_job(self, message_id, job_id, *, base_job):
        self.heartbeat_calls += 1
        return JobInfo(
            job_id=job_id,
            status="running",
            source=base_job.source,
            trigger_type=base_job.trigger_type,
            created_at=base_job.created_at,
            started_at=base_job.started_at,
            attempt_count=base_job.attempt_count,
            last_heartbeat_at=time.time(),
        )

    def is_cancel_requested(self, job_id):
        return self.cancel_requested


class _FakeDeleteResult:
    def __init__(self, deleted_count: int = 0):
        self.deleted_count = deleted_count


class _FakeCollection:
    def delete_many(self, _query):
        return _FakeDeleteResult(0)


class _FakeStateCollection:
    def update_one(self, _query, _update, upsert=False):
        return None


class SlowOrchestrator:
    def __init__(self):
        self.database = {
            "raw_documents": _FakeCollection(),
            "source_records": _FakeCollection(),
            "crawl_sessions": _FakeCollection(),
            "dataset_state": _FakeStateCollection(),
        }

    def crawl_source(self, source, *, trigger_type, progress_callback=None, should_cancel=None):
        time.sleep(1.1)
        if should_cancel is not None and should_cancel():
            raise ScrapeCancellationRequested("scrape_cancel_requested")
        if progress_callback is not None:
            progress_callback(
                {
                    "event": "source_crawl_started",
                    "source": source,
                    "status": "running",
                    "message": "Source crawl started",
                }
            )
        return {"status": "success", "source": source, "trigger_type": trigger_type}

    def drain_pending_writes(self, *, batch_size):
        return {"dequeued": 0, "processed": 0, "requeued": 0, "dead_lettered": 0}


class RefreshOrchestrator:
    def __init__(self):
        self.database = {"dataset_state": _FakeStateCollection()}

    def crawl_active_sources(
        self,
        *,
        trigger_type,
        dataset_generation=None,
        progress_callback=None,
        should_cancel=None,
    ):
        assert trigger_type == "refresh"
        assert dataset_generation == "generation_1"
        if should_cancel is not None and should_cancel():
            raise ScrapeCancellationRequested("scrape_cancel_requested")
        if progress_callback is not None:
            progress_callback(
                {
                    "event": "source_crawl_started",
                    "source": "ozgurkocaeli.com.tr",
                    "status": "running",
                    "message": "Source crawl started",
                    "details": {"listing_count": 2},
                }
            )
        return {
            "active_sources": 1,
            "processed_sources": 1,
            "skipped_sources": 0,
            "sessions": [
                {
                    "domain": "ozgurkocaeli.com.tr",
                    "status": "success",
                    "listing_count": 2,
                    "fetched_count": 2,
                    "parsed_count": 2,
                    "failed_count": 0,
                }
            ],
        }

    def drain_pending_writes(self, *, batch_size):
        return {"dequeued": 0, "processed": 0, "requeued": 0, "dead_lettered": 0}


class PartialRefreshOrchestrator:
    def __init__(self):
        self.database = {"dataset_state": _FakeStateCollection()}

    def crawl_active_sources(
        self,
        *,
        trigger_type,
        dataset_generation=None,
        progress_callback=None,
        should_cancel=None,
    ):
        assert trigger_type == "refresh"
        assert dataset_generation == "generation_1"
        if should_cancel is not None and should_cancel():
            raise ScrapeCancellationRequested("scrape_cancel_requested")
        if progress_callback is not None:
            progress_callback(
                {
                    "event": "source_crawl_started",
                    "source": "ozgurkocaeli.com.tr",
                    "status": "running",
                    "message": "Source crawl started",
                }
            )
        return {
            "active_sources": 1,
            "processed_sources": 1,
            "skipped_sources": 0,
            "sessions": [
                {
                    "domain": "ozgurkocaeli.com.tr",
                    "status": "partial",
                    "listing_count": 2,
                    "fetched_count": 2,
                    "parsed_count": 1,
                    "failed_count": 1,
                }
            ],
        }

    def drain_pending_writes(self, *, batch_size):
        return {"dequeued": 0, "processed": 0, "requeued": 0, "dead_lettered": 0}


def test_execute_job_with_heartbeat_touches_running_job(monkeypatch):
    monkeypatch.setattr("app.workers.job_worker.settings.job_heartbeat_seconds", 1)

    manager = FakeJobManager()
    running_job = JobInfo(
        job_id="job_123",
        status="running",
        source="ozgurkocaeli.com.tr",
        trigger_type="manual",
        created_at=100.0,
        started_at=101.0,
    )

    result, updated_job = _execute_job_with_heartbeat(
        manager,
        SlowOrchestrator(),
        "1710000000000-0",
        running_job,
    )

    assert manager.heartbeat_calls >= 1
    assert updated_job.last_heartbeat_at is not None
    assert result["status"] == "success"
    assert result["queue_drain"]["processed"] == 0


def test_execute_job_with_heartbeat_raises_when_cancel_requested(monkeypatch):
    monkeypatch.setattr("app.workers.job_worker.settings.job_heartbeat_seconds", 1)

    manager = FakeJobManager()
    manager.cancel_requested = True
    running_job = JobInfo(
        job_id="job_cancel_1",
        status="running",
        source="ozgurkocaeli.com.tr",
        trigger_type="manual",
        created_at=100.0,
        started_at=101.0,
    )

    with pytest.raises(ScrapeCancellationRequested):
        _execute_job_with_heartbeat(
            manager,
            SlowOrchestrator(),
            "1710000000000-0",
            running_job,
        )


def test_is_retryable_error_only_for_transient_failures():
    assert _is_retryable_error(TimeoutError("temporary")) is True
    assert _is_retryable_error(ValueError("permanent")) is False


def test_collect_refresh_success_allows_intentional_skipped_sources():
    summary = {
        "active_sources": 3,
        "processed_sources": 2,
        "skipped_sources": 1,
        "skipped_session_reasons": ["skipped_by_config"],
        "sessions": [
            {"status": "success", "domain": "ozgurkocaeli.com.tr"},
            {"status": "success", "domain": "cagdaskocaeli.com.tr"},
        ],
    }

    assert _collect_refresh_success(summary) is None


def test_collect_refresh_success_rejects_unexpected_skipped_sources():
    summary = {
        "active_sources": 2,
        "processed_sources": 1,
        "skipped_sources": 1,
        "skipped_session_reasons": ["lease_not_acquired"],
        "sessions": [
            {"status": "success", "domain": "ozgurkocaeli.com.tr"},
        ],
    }

    assert _collect_refresh_success(summary) == "refresh_skipped_sources_present"


def test_run_scrape_job_refresh_preserves_active_dataset(monkeypatch):
    published_events = []

    class CleanupResult:
        generation = "generation_1"
        deleted_counts = {"raw_documents": 2, "source_records": 2}
        total_deleted = 4

    def fail_if_reset(_database):
        raise AssertionError("refresh should not reset the active dataset upfront")

    monkeypatch.setattr("app.workers.job_worker._publish", lambda event: published_events.append(event))
    monkeypatch.setattr("app.workers.job_worker.reset_scraped_news_workspace", fail_if_reset)
    monkeypatch.setattr("app.workers.job_worker.begin_refresh_generation", lambda _database: "generation_1")
    monkeypatch.setattr("app.workers.job_worker.activate_generation", lambda _database, _generation: None)
    monkeypatch.setattr("app.workers.job_worker.cleanup_refresh_data", lambda _database, active_generation: CleanupResult())

    result = _run_scrape_job(
        RefreshOrchestrator(),
        None,
        "refresh",
        "job_refresh_1",
    )

    assert "pre_scrape_reset" not in result
    assert result["refresh_cleanup"]["status"] == "completed"
    event_names = [event.event for event in published_events]
    assert "refresh_preserving_active_dataset" in event_names
    assert "source_crawl_started" in event_names
    assert "refresh_cleanup_completed" in event_names


def test_run_scrape_job_refresh_promotes_partial_when_no_active_dataset(monkeypatch):
    published_events = []

    class CleanupResult:
        generation = "generation_1"
        deleted_counts = {"raw_documents": 0, "source_records": 0}
        total_deleted = 0

    monkeypatch.setattr("app.workers.job_worker._publish", lambda event: published_events.append(event))
    monkeypatch.setattr("app.workers.job_worker.begin_refresh_generation", lambda _database: "generation_1")
    monkeypatch.setattr(
        "app.workers.job_worker.get_dataset_generation_state",
        lambda _database: DatasetGenerationState(
            active_generation=None,
            pending_refresh_generation="generation_1",
        ),
    )
    monkeypatch.setattr("app.workers.job_worker.activate_generation", lambda _database, _generation: None)
    monkeypatch.setattr("app.workers.job_worker.cleanup_refresh_data", lambda _database, active_generation: CleanupResult())

    result = _run_scrape_job(
        PartialRefreshOrchestrator(),
        None,
        "refresh",
        "job_refresh_partial_promote",
    )

    assert result["refresh_cleanup"]["status"] == "completed_with_partial"
    assert result["refresh_cleanup"]["reason"] == "refresh_not_fully_successful"
    event_names = [event.event for event in published_events]
    assert "refresh_partial_cutover_started" in event_names
    assert "refresh_partial_cutover_completed" in event_names
    assert "refresh_cleanup_skipped" not in event_names


def test_run_scrape_job_refresh_discards_partial_when_active_dataset_exists(monkeypatch):
    published_events = []

    class DiscardResult:
        generation = "generation_1"
        deleted_counts = {"raw_documents": 10, "source_records": 10}
        total_deleted = 20

    monkeypatch.setattr("app.workers.job_worker._publish", lambda event: published_events.append(event))
    monkeypatch.setattr("app.workers.job_worker.begin_refresh_generation", lambda _database: "generation_1")
    monkeypatch.setattr(
        "app.workers.job_worker.get_dataset_generation_state",
        lambda _database: DatasetGenerationState(
            active_generation="existing_generation",
            pending_refresh_generation="generation_1",
        ),
    )
    monkeypatch.setattr(
        "app.workers.job_worker.discard_refresh_generation",
        lambda _database, pending_generation: DiscardResult(),
    )
    monkeypatch.setattr(
        "app.workers.job_worker.clear_pending_refresh_generation",
        lambda _database, expected_generation=None: None,
    )

    result = _run_scrape_job(
        PartialRefreshOrchestrator(),
        None,
        "refresh",
        "job_refresh_partial_discard",
    )

    assert result["refresh_cleanup"]["status"] == "discarded"
    assert result["refresh_cleanup"]["reason"] == "refresh_not_fully_successful"
    event_names = [event.event for event in published_events]
    assert "refresh_cleanup_skipped" in event_names
    assert "refresh_partial_cutover_completed" not in event_names


def test_run_scrape_job_raises_when_bootstrap_cancel_requested(monkeypatch):
    published_events = []
    orchestrator = SlowOrchestrator()

    monkeypatch.setattr("app.workers.job_worker._publish", lambda event: published_events.append(event))

    with pytest.raises(ScrapeCancellationRequested):
        _run_scrape_job(
            orchestrator,
            None,
            "bootstrap",
            "job_bootstrap_cancel",
            should_cancel=lambda: True,
        )

    assert any(event.event == "dataset_reset" for event in published_events)
