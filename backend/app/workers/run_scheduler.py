from __future__ import annotations

import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler

from app.scheduler.config import load_scheduler_config
from app.services.scrape_events import ScrapeEvent, get_scrape_event_publisher
from app.workers.job_manager import JobManager, JobQueueUnavailableError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _run_scheduled_crawl(job_manager: JobManager) -> None:
    try:
        job_id = job_manager.submit_scheduled_crawl_job()
        if job_id is None:
            logger.info("scheduler.job_skipped", extra={"reason": "scheduled_job_already_queued"})
            get_scrape_event_publisher().publish(
                ScrapeEvent(
                    event="scheduler_job_skipped",
                    message="Scheduled crawl was skipped because one is already queued",
                    trigger_type="scheduled",
                    status="skipped",
                )
            )
            return

        get_scrape_event_publisher().publish(
            ScrapeEvent(
                event="job_submitted",
                message="Scheduled scrape job queued",
                job_id=job_id,
                trigger_type="scheduled",
                status="pending",
            )
        )
        logger.info("scheduler.job_submitted", extra={"job_id": job_id})

    except JobQueueUnavailableError:
        get_scrape_event_publisher().publish(
            ScrapeEvent(
                event="scheduler_submit_failed",
                message="Scheduler could not submit job — Redis unavailable",
                trigger_type="scheduled",
                status="error",
            )
        )
        logger.exception("scheduler.submit_failed")
    except Exception as exc:
        get_scrape_event_publisher().publish(
            ScrapeEvent(
                event="scheduler_submit_failed",
                message="Scheduler could not submit job — unexpected error",
                trigger_type="scheduled",
                status="error",
                details={"error": type(exc).__name__},
            )
        )
        logger.exception("scheduler.submit_failed")


def main() -> None:
    config = load_scheduler_config()

    if not config.enabled:
        logger.info("scheduler.disabled - exiting")
        sys.exit(0)

    job_manager = JobManager()
    if not job_manager.available:
        logger.error("scheduler.redis_unavailable - cannot start without Redis")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone=config.timezone)
    scheduler.add_job(
        _run_scheduled_crawl,
        trigger="interval",
        hours=config.interval_hours,
        id="scheduled_crawl_job",
        replace_existing=True,
        args=[job_manager],
    )

    def _shutdown(signum, _frame):
        logger.info("scheduler.signal_received", extra={"signal": signum})
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info(
        "scheduler.started",
        extra={
            "timezone": config.timezone,
            "interval_hours": config.interval_hours,
        },
    )
    scheduler.start()


if __name__ == "__main__":
    main()
