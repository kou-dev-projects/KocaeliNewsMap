import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .config import load_scheduler_config
from .jobs import run_scheduled_crawl


logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self) -> None:
        self._config = load_scheduler_config()
        self._scheduler = BackgroundScheduler(timezone=self._config.timezone)
        self._configured = False

    def configure(self) -> None:
        if self._configured or not self._config.enabled:
            return

        self._scheduler.add_job(
            run_scheduled_crawl,
            trigger="interval",
            hours=self._config.interval_hours,
            id="scheduled_crawl_job",
            replace_existing=True,
        )
        self._configured = True

    def start(self) -> None:
        if not self._config.enabled:
            logger.info("scheduler.disabled")
            return

        if not self._configured:
            self.configure()

        if not self._scheduler.running:
            self._scheduler.start()
            logger.info(
                "scheduler.started",
                extra={
                    "timezone": self._config.timezone,
                    "interval_hours": self._config.interval_hours,
                },
            )

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("scheduler.stopped")


scheduler_service = SchedulerService()
