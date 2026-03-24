from fastapi import HTTPException

from app.routes.scrape import trigger_scrape


class FakeOrchestrator:
    def crawl_active_sources(self, *, trigger_type: str):
        assert trigger_type == "manual"
        return {"status": "ok", "mode": "all"}

    def crawl_source(self, source: str, *, trigger_type: str):
        assert trigger_type == "manual"
        if source == "missing.com":
            raise ValueError("active_source_not_found: missing.com")
        return {"status": "ok", "mode": "single", "source": source}


def test_trigger_scrape_runs_all_sources(monkeypatch):
    monkeypatch.setattr("app.routes.scrape.ScrapeOrchestrator", FakeOrchestrator)

    result = trigger_scrape(None)

    assert result == {"status": "ok", "mode": "all"}


def test_trigger_scrape_runs_single_source(monkeypatch):
    monkeypatch.setattr("app.routes.scrape.ScrapeOrchestrator", FakeOrchestrator)

    result = trigger_scrape("ozgurkocaeli.com.tr")

    assert result == {
        "status": "ok",
        "mode": "single",
        "source": "ozgurkocaeli.com.tr",
    }


def test_trigger_scrape_raises_404_for_missing_source(monkeypatch):
    monkeypatch.setattr("app.routes.scrape.ScrapeOrchestrator", FakeOrchestrator)

    try:
        trigger_scrape("missing.com")
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "active_source_not_found: missing.com"
    else:
        raise AssertionError("HTTPException was expected")
