from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.services.scrape_reset import (
    ScrapeRefreshCleanupResult,
    cleanup_pending_refresh_data,
    cleanup_stale_refresh_data,
)
from app.workers.job_manager import JobManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrapeTriggerResult:
    status: str
    trigger_type: str
    job_id: str | None = None
    reason: str | None = None


def has_scraped_news_data(database: Any) -> bool:
    return database["source_records"].count_documents({}, limit=1) > 0


def start_bootstrap_scrape_if_needed(
    database: Any,
    manager: JobManager,
) -> ScrapeTriggerResult:
    if has_scraped_news_data(database):
        logger.info(
            "scrape.bootstrap.skipped",
            extra={"reason": "data_exists"},
        )
        return ScrapeTriggerResult(
            status="already_initialized",
            trigger_type="bootstrap",
            reason="data_exists",
        )

    job_id = manager.submit_job(trigger_type="bootstrap")
    logger.info(
        "scrape.bootstrap.started",
        extra={"job_id": job_id, "trigger_type": "bootstrap"},
    )
    return ScrapeTriggerResult(
        status="started",
        trigger_type="bootstrap",
        job_id=job_id,
    )


def start_refresh_scrape(
    database: Any,
    manager: JobManager,
) -> ScrapeTriggerResult:
    job_id = manager.submit_job(trigger_type="refresh")
    logger.info(
        "scrape.refresh.started",
        extra={"job_id": job_id, "trigger_type": "refresh"},
    )
    return ScrapeTriggerResult(
        status="started",
        trigger_type="refresh",
        job_id=job_id,
    )


def cleanup_refresh_data(
    database: Any,
    *,
    active_generation: str,
) -> ScrapeRefreshCleanupResult:
    return cleanup_stale_refresh_data(
        database,
        active_generation=active_generation,
    )


def discard_refresh_generation(
    database: Any,
    *,
    pending_generation: str,
) -> ScrapeRefreshCleanupResult:
    return cleanup_pending_refresh_data(
        database,
        pending_generation=pending_generation,
    )
