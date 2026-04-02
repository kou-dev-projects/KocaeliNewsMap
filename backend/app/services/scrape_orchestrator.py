from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.services.scrape_reset import ScrapeResetResult, reset_scraped_news_data
from app.workers.job_manager import JobManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrapeTriggerResult:
    status: str
    trigger_type: str
    job_id: str | None = None
    reason: str | None = None
    reset_result: ScrapeResetResult | None = None


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
    reset_result = reset_scraped_news_data(database)
    job_id = manager.submit_job(trigger_type="refresh")
    logger.info(
        "scrape.refresh.started",
        extra={
            "job_id": job_id,
            "trigger_type": "refresh",
            "deleted_counts": reset_result.deleted_counts,
            "total_deleted": reset_result.total_deleted,
        },
    )
    return ScrapeTriggerResult(
        status="started",
        trigger_type="refresh",
        job_id=job_id,
        reset_result=reset_result,
    )
