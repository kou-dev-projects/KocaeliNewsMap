from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.scheduler import ScrapeOrchestrator


router = APIRouter(prefix="/scrape", tags=["scrape"])


@router.post("/trigger")
def trigger_scrape(source: str | None = Query(default=None)) -> dict:
    orchestrator = ScrapeOrchestrator()

    try:
        if source:
            return orchestrator.crawl_source(source, trigger_type="manual")
        return orchestrator.crawl_active_sources(trigger_type="manual")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
