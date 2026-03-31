from __future__ import annotations

from collections import namedtuple
from unittest.mock import MagicMock, patch

import app.workers.job_worker as worker_module
from app.services.scrape_events import ScrapeEvent
from app.workers.job_manager import JobInfo, JobQueueUnavailableError
from app.workers.run_scheduler import _run_scheduled_crawl



FakeClaimed = namedtuple("FakeClaimed", ["message_id", "job"])


def _make_job(**kwargs) -> JobInfo:
    defaults = dict(
        job_id="job_abc",
        status="pending",
        source="ozgurkocaeli.com.tr",
        trigger_type="manual",
        created_at=1000.0,
        attempt_count=0,
    )
    defaults.update(kwargs)
    return JobInfo(**defaults)


def _capture_publisher(monkeypatch) -> list[ScrapeEvent]:
    """Patch get_scrape_event_publisher() and return the list of published events."""
    published: list[ScrapeEvent] = []
    fake_pub = MagicMock()
    fake_pub.publish.side_effect = published.append
    monkeypatch.setattr("app.workers.job_worker.get_scrape_event_publisher", lambda: fake_pub)
    return published


def _capture_scheduler_publisher(monkeypatch) -> list[ScrapeEvent]:
    published: list[ScrapeEvent] = []
    fake_pub = MagicMock()
    fake_pub.publish.side_effect = published.append
    monkeypatch.setattr("app.workers.run_scheduler.get_scrape_event_publisher", lambda: fake_pub)
    return published


def _build_manager_for_one_job(
    job: JobInfo,
    running_job: JobInfo,
    completed_job: JobInfo | None = None,
    failed_job: JobInfo | None = None,
    retried_job: JobInfo | None = None,
    mark_failed_exc: Exception | None = None,
    mark_running_exc: Exception | None = None,
) -> MagicMock:
    manager = MagicMock()
    manager.available = True

    dequeue_calls = [0]

    def _dequeue(timeout=5):
        dequeue_calls[0] += 1
        if dequeue_calls[0] == 1:
            return FakeClaimed(message_id="stream_msg_1", job=job)
        worker_module._SHUTDOWN = True
        return None

    manager.dequeue_job.side_effect = _dequeue
    manager.get_job.return_value = job

    if mark_running_exc:
        manager.mark_running.side_effect = mark_running_exc
    else:
        manager.mark_running.return_value = running_job

    if mark_failed_exc:
        manager.mark_failed.side_effect = mark_failed_exc

    manager.mark_failed.return_value = failed_job or _make_job(status="failed")
    manager.mark_completed.return_value = completed_job or _make_job(status="completed")
    manager.retry_job.return_value = retried_job or _make_job(status="pending", attempt_count=1)
    manager.ack_job.return_value = None
    return manager


def _run_main_with(manager, orchestrator_result=None, job_exc=None, monkeypatch=None):
    """Run main() with fully mocked dependencies stopping after one job."""
    worker_module._SHUTDOWN = False

    def _fake_manager_cls():
        return manager

    def _fake_orchestrator_cls():
        return MagicMock()

    if job_exc:
        def _fake_execute(jm, orc, mid, rj):
            raise job_exc
    else:
        def _fake_execute(jm, orc, mid, rj):
            return orchestrator_result or {"status": "success"}, rj

    with patch("app.workers.job_worker.JobManager", _fake_manager_cls):
        with patch("app.workers.job_worker.ScrapeOrchestrator", _fake_orchestrator_cls):
            with patch(
                "app.workers.job_worker._execute_job_with_heartbeat",
                side_effect=_fake_execute,
            ):
                worker_module.main()

    worker_module._SHUTDOWN = False




class TestJobWorkerEvents:

    def test_job_started_event_correct_contract(self, monkeypatch):
        job = _make_job()
        running = _make_job(status="running", attempt_count=1)
        completed = _make_job(status="completed", attempt_count=1)

        published = _capture_publisher(monkeypatch)
        manager = _build_manager_for_one_job(job, running, completed_job=completed)

        _run_main_with(manager)

        started = next((e for e in published if e.event == "job_started"), None)
        assert started is not None, "job_started event was not published"
        assert started.status == "running"
        assert started.job_id == "job_abc"
        assert started.source == "ozgurkocaeli.com.tr"
        assert started.trigger_type == "manual"
        assert started.attempt_count == 1

    def test_job_completed_event_correct_contract(self, monkeypatch):
        job = _make_job()
        running = _make_job(status="running", attempt_count=1)
        completed = _make_job(status="completed", attempt_count=1)

        published = _capture_publisher(monkeypatch)
        manager = _build_manager_for_one_job(job, running, completed_job=completed)

        _run_main_with(manager, orchestrator_result={"status": "success"})

        completed_evt = next((e for e in published if e.event == "job_completed"), None)
        assert completed_evt is not None, "job_completed event was not published"
        assert completed_evt.status == "completed"
        assert completed_evt.job_id == "job_abc"
        assert completed_evt.details == {"result_status": "success"}

    def test_job_failed_event_correct_contract(self, monkeypatch):
        job = _make_job()
        running = _make_job(status="running")
        failed = _make_job(status="failed")

        published = _capture_publisher(monkeypatch)
        manager = _build_manager_for_one_job(job, running, failed_job=failed)

        _run_main_with(manager, job_exc=RuntimeError("scrape boom"))

        failed_evt = next((e for e in published if e.event == "job_failed"), None)
        assert failed_evt is not None, "job_failed event was not published"
        assert failed_evt.status == "failed"
        assert failed_evt.details is not None
        assert "RuntimeError" in failed_evt.details.get("error", "")

    def test_job_retrying_event_correct_contract(self, monkeypatch):
        job = _make_job()
        running = _make_job(status="running", attempt_count=0)
        retried = _make_job(status="pending", attempt_count=1)

        published = _capture_publisher(monkeypatch)
        manager = _build_manager_for_one_job(job, running, retried_job=retried)

        monkeypatch.setattr("app.workers.job_worker.settings.job_max_attempts", 3)

        _run_main_with(manager, job_exc=TimeoutError("timed out"))

        retrying_evt = next((e for e in published if e.event == "job_retrying"), None)
        assert retrying_evt is not None, "job_retrying event was not published"
        assert retrying_evt.status == "pending"
        assert retrying_evt.attempt_count == 1
        assert "TimeoutError" in retrying_evt.details.get("error", "")

    def test_job_stale_ack_event_published_after_ack(self, monkeypatch):
        """stale_ack must be published only AFTER ack_job() succeeds."""
        terminal_job = _make_job(status="completed")

        published = _capture_publisher(monkeypatch)

        manager = MagicMock()
        manager.available = True

        dequeue_calls = [0]

        def _dequeue(timeout=5):
            dequeue_calls[0] += 1
            if dequeue_calls[0] == 1:
                return FakeClaimed(message_id="stale_msg", job=terminal_job)
            worker_module._SHUTDOWN = True
            return None

        manager.dequeue_job.side_effect = _dequeue
        manager.get_job.return_value = terminal_job
        manager.ack_job.return_value = None

        worker_module._SHUTDOWN = False

        with patch("app.workers.job_worker.JobManager", lambda: manager):
            with patch("app.workers.job_worker.ScrapeOrchestrator", MagicMock):
                worker_module.main()

        worker_module._SHUTDOWN = False

        stale_evt = next((e for e in published if e.event == "job_stale_ack"), None)
        assert stale_evt is not None, "job_stale_ack event was not published"
        assert stale_evt.status == "completed"

       
        manager.ack_job.assert_called_once_with("stale_msg", job=terminal_job)

    def test_no_started_event_if_mark_running_fails(self, monkeypatch):
        """If mark_running raises, job_started must NOT be published."""
        job = _make_job()
        running = _make_job(status="running")

        published = _capture_publisher(monkeypatch)
        manager = _build_manager_for_one_job(
            job, running, mark_running_exc=JobQueueUnavailableError("oops")
        )

        _run_main_with(manager)

        assert not any(e.event == "job_started" for e in published)

    def test_job_heartbeat_event_correct_contract(self, monkeypatch):
        from concurrent.futures import TimeoutError

        published = _capture_publisher(monkeypatch)

        running_job = _make_job(status="running", attempt_count=1)
        heartbeat_job = _make_job(status="running", attempt_count=1)

        manager = MagicMock()
        manager.heartbeat_job.return_value = heartbeat_job

        call_count = [0]

        def fake_result(self_future, timeout=None):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TimeoutError("Simulated timeout")
            return {"status": "success", "queue_drain": {}}

        monkeypatch.setattr("concurrent.futures.Future.result", fake_result)

        fake_orchestrator = MagicMock()
        # Not using side_effect because future result is already mocked
        fake_orchestrator.crawl_source.return_value = {}
        fake_orchestrator.drain_pending_writes.return_value = {}

        from app.workers.job_worker import _execute_job_with_heartbeat

        result, _ = _execute_job_with_heartbeat(
            manager, fake_orchestrator, "msg_1", running_job,
        )

        hb_evt = next((e for e in published if e.event == "job_heartbeat"), None)
        assert hb_evt is not None, "job_heartbeat event was not published"
        assert hb_evt.status == "running"
        assert hb_evt.job_id == "job_abc"
        assert hb_evt.attempt_count == 1


class TestRunSchedulerEvents:

    def test_job_submitted_event_on_success(self, monkeypatch):
        published = _capture_scheduler_publisher(monkeypatch)

        manager = MagicMock()
        manager.submit_scheduled_crawl_job.return_value = "sched_job_1"

        _run_scheduled_crawl(manager)

        evt = next((e for e in published if e.event == "job_submitted"), None)
        assert evt is not None, "job_submitted event was not published"
        assert evt.job_id == "sched_job_1"
        assert evt.trigger_type == "scheduled"
        assert evt.status == "pending"

    def test_scheduler_job_skipped_event_when_already_queued(self, monkeypatch):
        published = _capture_scheduler_publisher(monkeypatch)

        manager = MagicMock()
        manager.submit_scheduled_crawl_job.return_value = None  # lock held

        _run_scheduled_crawl(manager)

        evt = next((e for e in published if e.event == "scheduler_job_skipped"), None)
        assert evt is not None, "scheduler_job_skipped event was not published"
        assert evt.trigger_type == "scheduled"
        assert evt.status == "skipped"

    def test_scheduler_submit_failed_event_on_queue_unavailable(self, monkeypatch):
        published = _capture_scheduler_publisher(monkeypatch)

        manager = MagicMock()
        manager.submit_scheduled_crawl_job.side_effect = JobQueueUnavailableError("redis down")

        _run_scheduled_crawl(manager)

        evt = next((e for e in published if e.event == "scheduler_submit_failed"), None)
        assert evt is not None, "scheduler_submit_failed event was not published"
        assert evt.trigger_type == "scheduled"
        assert evt.status == "error"

    def test_scheduler_submit_failed_event_on_generic_exception(self, monkeypatch):
        published = _capture_scheduler_publisher(monkeypatch)

        manager = MagicMock()
        manager.submit_scheduled_crawl_job.side_effect = ValueError("unexpected")

        _run_scheduled_crawl(manager)

        evt = next((e for e in published if e.event == "scheduler_submit_failed"), None)
        assert evt is not None, "scheduler_submit_failed event was not published for generic exception"
        assert evt.status == "error"
        assert evt.details is not None
        assert evt.details.get("error") == "ValueError"
