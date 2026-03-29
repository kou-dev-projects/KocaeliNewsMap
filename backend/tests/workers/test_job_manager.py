from unittest.mock import MagicMock

import pytest

from app.workers.job_manager import (
    JobInfo,
    JobManager,
    JobQueueUnavailableError,
)


def test_available_retries_connection_after_initial_failure(monkeypatch):
    calls = {"count": 0}

    def fake_from_url(*args, **kwargs):
        calls["count"] += 1
        client = MagicMock()
        if calls["count"] == 1:
            client.ping.side_effect = RuntimeError("redis down")
        else:
            client.ping.return_value = True
            client.xgroup_create.return_value = True
        return client

    monkeypatch.setattr("app.workers.job_manager.redis.from_url", fake_from_url)

    manager = JobManager(redis_url="redis://example:6379/0")

    assert manager.available is True
    assert calls["count"] == 2


def test_mark_completed_recreates_missing_job_from_base_job(monkeypatch):
    client = MagicMock()
    client.ping.return_value = True
    client.get.return_value = None

    monkeypatch.setattr("app.workers.job_manager.redis.from_url", lambda *args, **kwargs: client)

    manager = JobManager(redis_url="redis://example:6379/0")
    base_job = JobInfo(
        job_id="job_123",
        status="running",
        source="ozgurkocaeli.com.tr",
        trigger_type="manual",
        created_at=100.0,
        started_at=101.0,
    )

    updated = manager.mark_completed(
        "job_123",
        {"status": "success"},
        base_job=base_job,
    )

    assert updated.status == "completed"
    assert updated.result == {"status": "success"}
    client.setex.assert_called_once()


def test_heartbeat_job_updates_state_and_touches_stream_claim(monkeypatch):
    client = MagicMock()
    client.ping.return_value = True
    client.get.return_value = None

    monkeypatch.setattr("app.workers.job_manager.redis.from_url", lambda *args, **kwargs: client)

    manager = JobManager(redis_url="redis://example:6379/0", consumer_name="worker:test")
    base_job = JobInfo(
        job_id="job_123",
        status="running",
        source=None,
        trigger_type="manual",
        created_at=100.0,
        started_at=101.0,
        attempt_count=1,
    )

    updated = manager.heartbeat_job("1710000000000-0", "job_123", base_job=base_job)

    assert updated.status == "running"
    assert updated.attempt_count == 1
    assert updated.last_heartbeat_at is not None
    client.xclaim.assert_called_once()
    client.setex.assert_called_once()


def test_retry_job_requeues_same_job_with_incremented_attempt_count(monkeypatch):
    client = MagicMock()
    client.ping.return_value = True
    pipe = MagicMock()
    pipe.execute.return_value = [True, 1, 1, "1710000000001-0"]
    client.pipeline.return_value = pipe

    monkeypatch.setattr("app.workers.job_manager.redis.from_url", lambda *args, **kwargs: client)

    manager = JobManager(redis_url="redis://example:6379/0", consumer_name="worker:test")
    base_job = JobInfo(
        job_id="job_123",
        status="running",
        source="ozgurkocaeli.com.tr",
        trigger_type="manual",
        created_at=100.0,
        started_at=101.0,
        attempt_count=1,
    )

    retried = manager.retry_job("1710000000000-0", base_job, "temporary error")

    assert retried.status == "pending"
    assert retried.attempt_count == 2
    pipe.xack.assert_called_once()
    pipe.xdel.assert_called_once()
    pipe.xadd.assert_called_once()


def test_submit_scheduled_crawl_job_returns_none_when_lock_exists(monkeypatch):
    client = MagicMock()
    client.ping.return_value = True
    client.xgroup_create.return_value = True
    client.set.return_value = None

    monkeypatch.setattr("app.workers.job_manager.redis.from_url", lambda *args, **kwargs: client)

    manager = JobManager(redis_url="redis://example:6379/0")

    assert manager.submit_scheduled_crawl_job() is None


def test_get_job_raises_queue_unavailable_when_redis_fetch_fails(monkeypatch):
    client = MagicMock()
    client.ping.return_value = True
    client.get.side_effect = RuntimeError("redis down")

    monkeypatch.setattr("app.workers.job_manager.redis.from_url", lambda *args, **kwargs: client)

    manager = JobManager(redis_url="redis://example:6379/0")

    with pytest.raises(JobQueueUnavailableError):
        manager.get_job("job_123")


def test_default_consumer_name_includes_runtime_suffix(monkeypatch):
    client = MagicMock()
    client.ping.return_value = True
    client.xgroup_create.return_value = True

    monkeypatch.setattr("app.workers.job_manager.redis.from_url", lambda *args, **kwargs: client)
    monkeypatch.setattr("app.workers.job_manager.settings.worker_id", "worker")

    manager = JobManager(redis_url="redis://example:6379/0")

    assert manager._consumer_name.startswith("worker:")
    assert manager._consumer_name.count(":") >= 3
