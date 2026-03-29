import pytest
from fastapi import HTTPException

from app.routes.scrape import _RATE_LIMITER_STATE, trigger_scrape


class FakeOrchestrator:
    def crawl_active_sources(self, *, trigger_type: str):
        assert trigger_type == "manual"
        return {"status": "ok", "mode": "all"}

    def crawl_source(self, source: str, *, trigger_type: str):
        assert trigger_type == "manual"
        if source == "missing.com":
            raise ValueError("active_source_not_found: missing.com")
        return {"status": "ok", "mode": "single", "source": source}


class FakeRequestClient:
    def __init__(self, host: str):
        self.host = host


class FakeRequest:
    def __init__(self, host: str = "127.0.0.1", headers: dict[str, str] | None = None):
        self.client = FakeRequestClient(host)
        self.headers = headers or {}


@pytest.fixture(autouse=True)
def reset_scrape_route_state(monkeypatch):
    _RATE_LIMITER_STATE.clear()
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_api_key", None)
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_rate_limit_enabled", True)
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_rate_limit_requests", 5)
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_rate_limit_window_seconds", 60)


def test_trigger_scrape_runs_all_sources(monkeypatch):
    monkeypatch.setattr("app.routes.scrape.ScrapeOrchestrator", FakeOrchestrator)

    result = trigger_scrape(request=FakeRequest(), source=None)

    assert result == {"status": "ok", "mode": "all"}


def test_trigger_scrape_runs_single_source(monkeypatch):
    monkeypatch.setattr("app.routes.scrape.ScrapeOrchestrator", FakeOrchestrator)

    result = trigger_scrape(request=FakeRequest(), source="ozgurkocaeli.com.tr")

    assert result == {
        "status": "ok",
        "mode": "single",
        "source": "ozgurkocaeli.com.tr",
    }


def test_trigger_scrape_raises_404_for_missing_source(monkeypatch):
    monkeypatch.setattr("app.routes.scrape.ScrapeOrchestrator", FakeOrchestrator)

    try:
        trigger_scrape(request=FakeRequest(), source="missing.com")
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "active_source_not_found: missing.com"
    else:
        raise AssertionError("HTTPException was expected")


def test_trigger_scrape_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setattr("app.routes.scrape.ScrapeOrchestrator", FakeOrchestrator)
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_api_key", "secret-token")

    with pytest.raises(HTTPException) as exc_info:
        trigger_scrape(request=FakeRequest(), source=None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "unauthorized_scrape_trigger"


def test_trigger_scrape_accepts_valid_api_key(monkeypatch):
    monkeypatch.setattr("app.routes.scrape.ScrapeOrchestrator", FakeOrchestrator)
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_api_key", "secret-token")

    result = trigger_scrape(
        request=FakeRequest(),
        source="ozgurkocaeli.com.tr",
        x_api_key="secret-token",
    )

    assert result == {
        "status": "ok",
        "mode": "single",
        "source": "ozgurkocaeli.com.tr",
    }


def test_trigger_scrape_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr("app.routes.scrape.ScrapeOrchestrator", FakeOrchestrator)
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_rate_limit_requests", 1)
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_rate_limit_window_seconds", 60)

    request = FakeRequest(host="10.0.0.55")
    first = trigger_scrape(request=request, source=None)
    assert first == {"status": "ok", "mode": "all"}

    with pytest.raises(HTTPException) as exc_info:
        trigger_scrape(request=request, source=None)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "scrape_trigger_rate_limit_exceeded"
    assert exc_info.value.headers is not None
    assert "Retry-After" in exc_info.value.headers
