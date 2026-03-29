import logging

from .orchestrator import ScrapeOrchestrator

logger = logging.getLogger(__name__)
_ORCHESTRATOR: ScrapeOrchestrator | None = None


def _get_orchestrator() -> ScrapeOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = ScrapeOrchestrator()
    return _ORCHESTRATOR


def run_scheduled_crawl() -> None:
    summary = _get_orchestrator().crawl_active_sources(trigger_type="scheduled")
    logger.info("scheduler.job.crawl_finished", extra=summary)
