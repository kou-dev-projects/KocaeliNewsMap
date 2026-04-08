import json

import pytest
from fastapi import HTTPException

from app.routes.scrape import (
    bootstrap_scrape,
    get_job_status,
    refresh_scrape,
    trigger_scrape,
)
from app.services.scrape_orchestrator import ScrapeTriggerResult
from app.workers.job_manager import JobInfo, JobQueueUnavailableError


class FakeRequestClient:
    def __init__(self, host: str):
        self.host = host


class FakeRequest:
    def __init__(
        self,
        host: str = "127.0.0.1",
        headers: dict[str, str] | None = None,
        base_url: str = "http://testserver",
    ):
        self.client = FakeRequestClient(host)
        self.headers = headers or {}
        self.base_url = base_url

    def url_for(self, name: str, **path_params: str) -> str:
        if name != "get_job_status":
            raise AssertionError(f"unexpected route name: {name}")
        return f"{self.base_url}/api/v1/scrape/jobs/{path_params['job_id']}"


class FakeJobManager:
    def __init__(self):
        self.submitted: list[tuple[str | None, str]] = []
        self.jobs: dict[str, JobInfo] = {}

    def submit_job(self, source: str | None = None, trigger_type: str = "manual") -> str:
        self.submitted.append((source, trigger_type))
        job_id = "job_123"
        self.jobs[job_id] = JobInfo(
            job_id=job_id,
            status="pending",
            source=source,
            trigger_type=trigger_type,
            created_at=123.0,
        )
        return job_id

    def get_job(self, job_id: str) -> JobInfo | None:
        return self.jobs.get(job_id)


@pytest.fixture(autouse=True)
def reset_scrape_route_state(monkeypatch):
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_rate_limit_enabled", True)
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_rate_limit_requests", 5)
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_rate_limit_window_seconds", 60)
    monkeypatch.setattr("app.routes.scrape.settings.trusted_proxy_cidrs", "")
    monkeypatch.setattr("app.routes.scrape._get_rate_limit_redis", lambda: None)
    monkeypatch.setattr("app.routes.scrape._job_manager", None)
    monkeypatch.setattr("app.routes.scrape._rate_limit_redis", None)
    monkeypatch.setattr("app.routes.scrape._trusted_networks", None)


def test_trigger_scrape_returns_202_with_job_details(monkeypatch):
    manager = FakeJobManager()
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: manager)
    monkeypatch.setattr("app.routes.scrape._validate_source_exists", lambda source: None)

    result = trigger_scrape(request=FakeRequest(), source=None)
    payload = json.loads(result.body)

    assert result.status_code == 202
    assert payload == {
        "job_id": "job_123",
        "status": "pending",
        "status_url": "http://testserver/api/v1/scrape/jobs/job_123",
    }
    assert manager.submitted == [(None, "manual")]


def test_bootstrap_scrape_returns_200_when_data_already_initialized(monkeypatch):
    monkeypatch.setattr(
        "app.routes.scrape.start_bootstrap_scrape_if_needed",
        lambda database, manager: ScrapeTriggerResult(
            status="already_initialized",
            trigger_type="bootstrap",
            reason="data_exists",
        ),
    )
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: FakeJobManager())

    result = bootstrap_scrape(request=FakeRequest())
    payload = json.loads(result.body)

    assert result.status_code == 200
    assert payload == {
        "status": "already_initialized",
        "reason": "data_exists",
    }


def test_bootstrap_scrape_returns_202_when_job_is_started(monkeypatch):
    monkeypatch.setattr(
        "app.routes.scrape.start_bootstrap_scrape_if_needed",
        lambda database, manager: ScrapeTriggerResult(
            status="started",
            trigger_type="bootstrap",
            job_id="job_456",
        ),
    )
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: FakeJobManager())

    result = bootstrap_scrape(request=FakeRequest())
    payload = json.loads(result.body)

    assert result.status_code == 202
    assert payload == {
        "job_id": "job_456",
        "status": "pending",
        "status_url": "http://testserver/api/v1/scrape/jobs/job_456",
    }


def test_bootstrap_scrape_with_reset_clears_workspace_before_queue(monkeypatch):
    monkeypatch.setattr(
        "app.routes.scrape.start_bootstrap_scrape_if_needed",
        lambda database, manager: ScrapeTriggerResult(
            status="started",
            trigger_type="bootstrap",
            job_id="job_reset_1",
        ),
    )
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: FakeJobManager())
    monkeypatch.setattr(
        "app.routes.scrape.reset_scraped_news_workspace",
        lambda database: type(
            "ResetResult",
            (),
            {
                "deleted_counts": {
                    "raw_documents": 10,
                    "source_records": 8,
                    "crawl_sessions": 3,
                },
                "total_deleted": 21,
            },
        )(),
    )

    result = bootstrap_scrape(request=FakeRequest(), reset=True)
    payload = json.loads(result.body)

    assert result.status_code == 202
    assert payload == {
        "job_id": "job_reset_1",
        "status": "pending",
        "status_url": "http://testserver/api/v1/scrape/jobs/job_reset_1",
        "details": {
            "reset": {
                "deleted_counts": {
                    "raw_documents": 10,
                    "source_records": 8,
                    "crawl_sessions": 3,
                },
                "total_deleted": 21,
            }
        },
    }


def test_refresh_scrape_returns_202_with_job_details(monkeypatch):
    monkeypatch.setattr(
        "app.routes.scrape.start_refresh_scrape",
        lambda database, manager: ScrapeTriggerResult(
            status="started",
            trigger_type="refresh",
            job_id="job_789",
        ),
    )
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: FakeJobManager())

    result = refresh_scrape(request=FakeRequest())
    payload = json.loads(result.body)

    assert result.status_code == 202
    assert payload == {
        "job_id": "job_789",
        "status": "pending",
        "status_url": "http://testserver/api/v1/scrape/jobs/job_789",
    }


def test_trigger_scrape_normalizes_source_before_enqueue(monkeypatch):
    manager = FakeJobManager()
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: manager)
    monkeypatch.setattr("app.routes.scrape._validate_source_exists", lambda source: None)

    result = trigger_scrape(
        request=FakeRequest(),
        source=" OZGURKOCAELI.COM.TR ",
    )
    payload = json.loads(result.body)

    assert result.status_code == 202
    assert payload["job_id"] == "job_123"
    assert manager.submitted == [("ozgurkocaeli.com.tr", "manual")]


def test_trigger_scrape_raises_404_for_missing_source(monkeypatch):
    monkeypatch.setattr(
        "app.routes.scrape._validate_source_exists",
        lambda source: (_ for _ in ()).throw(
            HTTPException(status_code=404, detail="active_source_not_found: missing.com")
        ),
    )
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: FakeJobManager())

    with pytest.raises(HTTPException) as exc_info:
        trigger_scrape(request=FakeRequest(), source="missing.com")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "active_source_not_found: missing.com"


def test_trigger_scrape_runs_without_auth(monkeypatch):
    manager = FakeJobManager()
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: manager)
    monkeypatch.setattr("app.routes.scrape._validate_source_exists", lambda source: None)

    result = trigger_scrape(
        request=FakeRequest(),
        source="ozgurkocaeli.com.tr",
    )
    payload = json.loads(result.body)

    assert result.status_code == 202
    assert payload["job_id"] == "job_123"
    assert manager.submitted == [("ozgurkocaeli.com.tr", "manual")]


def test_trigger_scrape_returns_503_when_queue_unavailable(monkeypatch):
    manager = FakeJobManager()
    monkeypatch.setattr(
        manager,
        "submit_job",
        lambda source=None, trigger_type="manual": (_ for _ in ()).throw(
            JobQueueUnavailableError("redis down")
        ),
    )
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: manager)
    monkeypatch.setattr("app.routes.scrape._validate_source_exists", lambda source: None)

    with pytest.raises(HTTPException) as exc_info:
        trigger_scrape(request=FakeRequest(), source=None)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "job_queue_unavailable"


def test_get_job_status_returns_503_when_queue_unavailable(monkeypatch):
    manager = FakeJobManager()
    monkeypatch.setattr(
        manager,
        "get_job",
        lambda job_id: (_ for _ in ()).throw(JobQueueUnavailableError("redis down")),
    )
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: manager)

    with pytest.raises(HTTPException) as exc_info:
        get_job_status("job_123")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "job_queue_unavailable"


def test_trigger_scrape_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr("app.routes.scrape._validate_source_exists", lambda source: None)
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: FakeJobManager())
    monkeypatch.setattr(
        "app.routes.scrape._enforce_rate_limit",
        lambda client_id: (_ for _ in ()).throw(
            HTTPException(
                status_code=429,
                detail="scrape_trigger_rate_limit_exceeded",
                headers={"Retry-After": "60"},
            )
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        trigger_scrape(
            request=FakeRequest(host="10.0.0.55"),
            source=None,
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "scrape_trigger_rate_limit_exceeded"
    assert exc_info.value.headers is not None
    assert "Retry-After" in exc_info.value.headers


def test_get_job_status_returns_job_payload(monkeypatch):
    manager = FakeJobManager()
    manager.jobs["job_123"] = JobInfo(
        job_id="job_123",
        status="completed",
        source="ozgurkocaeli.com.tr",
        trigger_type="manual",
        created_at=100.0,
        started_at=101.0,
        completed_at=102.0,
        result={"status": "success"},
    )
    monkeypatch.setattr("app.routes.scrape._get_job_manager", lambda: manager)

    result = get_job_status("job_123")

    assert result == {
        "job_id": "job_123",
        "status": "completed",
        "source": "ozgurkocaeli.com.tr",
        "trigger_type": "manual",
        "created_at": 100.0,
        "attempt_count": 0,
        "started_at": 101.0,
        "completed_at": 102.0,
        "result": {"status": "success"},
    }
