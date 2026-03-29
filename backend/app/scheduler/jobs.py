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
    orchestrator = _get_orchestrator()
    queue_summary = orchestrator.drain_pending_writes(batch_size=50)
    if queue_summary.get("dequeued", 0) > 0:
        logger.info("scheduler.job.queue_drain_finished", extra=queue_summary)

    summary = orchestrator.crawl_active_sources(trigger_type="scheduled")
    logger.info("scheduler.job.crawl_finished", extra=summary)
