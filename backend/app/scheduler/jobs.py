import logging

from .orchestrator import ScrapeOrchestrator

logger = logging.getLogger(__name__)


def run_scheduled_crawl() -> None:
    summary = ScrapeOrchestrator().crawl_active_sources(trigger_type="scheduled")
    logger.info("scheduler.job.crawl_finished", extra=summary)
