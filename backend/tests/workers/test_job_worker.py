import time

from app.workers.job_manager import JobInfo
from app.workers.job_worker import _execute_job_with_heartbeat, _is_retryable_error


class FakeJobManager:
    def __init__(self):
        self.heartbeat_calls = 0

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


class SlowOrchestrator:
    def crawl_source(self, source, *, trigger_type):
        time.sleep(1.1)
        return {"status": "success", "source": source, "trigger_type": trigger_type}

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


def test_is_retryable_error_only_for_transient_failures():
    assert _is_retryable_error(TimeoutError("temporary")) is True
    assert _is_retryable_error(ValueError("permanent")) is False
