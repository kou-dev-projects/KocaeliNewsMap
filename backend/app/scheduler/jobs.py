from datetime import datetime, timezone
import logging


logger = logging.getLogger(__name__)


def run_healthcheck_job() -> None:
    logger.info(
        "scheduler.job.healthcheck",
        extra={
            "job": "healthcheck",
            "ran_at": datetime.now(timezone.utc).isoformat(),
        },
    )
