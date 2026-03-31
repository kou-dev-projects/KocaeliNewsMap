from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import logging
import signal
import sys
import time
from typing import Any

from app.scheduler.orchestrator import ScrapeOrchestrator
from app.services.scrape_events import ScrapeEvent, get_scrape_event_publisher
from app.workers.job_manager import JobManager, JobQueueUnavailableError, JobInfo
from app.settings import settings

try:
    from pymongo.errors import PyMongoError
except Exception:  # pragma: no cover
    PyMongoError = ()

try:
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover
    RedisError = ()

try:
    from requests import RequestException
except Exception:  # pragma: no cover
    RequestException = ()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_SHUTDOWN = False
_RETRYABLE_ERROR_TYPES = tuple(
    error_type
    for error_type in (
        TimeoutError,
        ConnectionError,
        OSError,
        PyMongoError,
        RedisError,
        RequestException,
    )
    if isinstance(error_type, type)
)


def _handle_signal(signum, _frame):
    global _SHUTDOWN
    logger.info("worker.signal_received", extra={"signal": signum})
    _SHUTDOWN = True


def _is_retryable_error(exc: Exception) -> bool:
    return isinstance(exc, _RETRYABLE_ERROR_TYPES)


def _publish(event: ScrapeEvent) -> None:
    """Fire-and-forget publish — never raises."""
    get_scrape_event_publisher().publish(event)


def _run_scrape_job(orchestrator: ScrapeOrchestrator, source: str | None, trigger_type: str) -> dict[str, Any]:
    if source:
        result = orchestrator.crawl_source(source, trigger_type=trigger_type)
    else:
        result = orchestrator.crawl_active_sources(trigger_type=trigger_type)

    drain_result = orchestrator.drain_pending_writes(batch_size=50)
    result["queue_drain"] = drain_result
    return result


def _execute_job_with_heartbeat(
    job_manager: JobManager,
    orchestrator: ScrapeOrchestrator,
    claimed_message_id: str,
    running_job: JobInfo,
) -> tuple[dict[str, Any], JobInfo]:
    heartbeat_seconds = max(settings.job_heartbeat_seconds, 1)
    current_job = running_job

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            _run_scrape_job,
            orchestrator,
            current_job.source,
            current_job.trigger_type,
        )

        while True:
            try:
                return future.result(timeout=heartbeat_seconds), current_job
            except FutureTimeoutError:
                try:
                    current_job = job_manager.heartbeat_job(
                        claimed_message_id,
                        current_job.job_id,
                        base_job=current_job,
                    )
                    _publish(
                        ScrapeEvent(
                            event="job_heartbeat",
                            message="Scrape job is still running",
                            job_id=current_job.job_id,
                            source=current_job.source,
                            trigger_type=current_job.trigger_type,
                            status="running",
                            attempt_count=current_job.attempt_count,
                        )
                    )
                except JobQueueUnavailableError:
                    logger.warning(
                        "worker.job_heartbeat_failed",
                        extra={"job_id": current_job.job_id},
                    )
                continue


def main() -> None:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    job_manager = JobManager()
    if not job_manager.available:
        logger.error("worker.redis_unavailable - cannot start without Redis")
        sys.exit(1)

    orchestrator = ScrapeOrchestrator()
    logger.info("worker.started - waiting for jobs")

    while not _SHUTDOWN:
        try:
            claimed = job_manager.dequeue_job(timeout=5)
        except JobQueueUnavailableError:
            logger.warning("worker.queue_unavailable")
            time.sleep(2)
            continue

        if claimed is None:
            continue

        try:
            job = job_manager.get_job(claimed.job.job_id) or claimed.job
        except JobQueueUnavailableError:
            logger.warning("worker.job_state_unavailable", extra={"job_id": claimed.job.job_id})
            time.sleep(2)
            continue

        if job.status in {"completed", "failed"}:
            try:
                job_manager.ack_job(claimed.message_id, job=job)
            except JobQueueUnavailableError:
                logger.warning("worker.job_final_ack_failed", extra={"job_id": job.job_id})
                time.sleep(2)
                continue

            _publish(
                ScrapeEvent(
                    event="job_stale_ack",
                    message="Stale job message acknowledged (already terminal)",
                    job_id=job.job_id,
                    source=job.source,
                    trigger_type=job.trigger_type,
                    status=job.status,
                )
            )
            continue

        logger.info(
            "worker.job.picked",
            extra={"job_id": job.job_id, "source": job.source, "trigger_type": job.trigger_type},
        )

        try:
            running_job = job_manager.mark_running(job.job_id, base_job=job)
        except (JobQueueUnavailableError, KeyError):
            logger.warning("worker.job_mark_running_failed", extra={"job_id": job.job_id})
            time.sleep(2)
            continue

        _publish(
            ScrapeEvent(
                event="job_started",
                message="Scrape job started",
                job_id=running_job.job_id,
                source=running_job.source,
                trigger_type=running_job.trigger_type,
                status="running",
                attempt_count=running_job.attempt_count,
            )
        )

        try:
            result, running_job = _execute_job_with_heartbeat(
                job_manager,
                orchestrator,
                claimed.message_id,
                running_job,
            )
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            max_attempts = max(settings.job_max_attempts, 1)
            should_retry = _is_retryable_error(exc) and (running_job.attempt_count + 1) < max_attempts

            if should_retry:
                try:
                    retried_job = job_manager.retry_job(
                        claimed.message_id,
                        running_job,
                        error_msg,
                    )
                    _publish(
                        ScrapeEvent(
                            event="job_retrying",
                            message="Scrape job will be retried",
                            job_id=retried_job.job_id,
                            source=retried_job.source,
                            trigger_type=retried_job.trigger_type,
                            status="pending",
                            attempt_count=retried_job.attempt_count,
                            details={"error": error_msg},
                        )
                    )
                    logger.warning(
                        "worker.job.retrying",
                        extra={
                            "job_id": retried_job.job_id,
                            "attempt_count": retried_job.attempt_count,
                            "max_attempts": max_attempts,
                            "error": error_msg[:200],
                        },
                    )
                except (JobQueueUnavailableError, KeyError):
                    logger.warning(
                        "worker.job_retry_persist_failed",
                        extra={"job_id": running_job.job_id},
                    )
                else:
                    retry_backoff = max(settings.job_retry_backoff_seconds, 0.0) * max(
                        retried_job.attempt_count,
                        1,
                    )
                    if retry_backoff > 0:
                        time.sleep(retry_backoff)
                    continue

            try:
                failed_job = job_manager.mark_failed(
                    running_job.job_id,
                    error_msg,
                    base_job=running_job,
                )
                _publish(
                    ScrapeEvent(
                        event="job_failed",
                        message="Scrape job failed",
                        job_id=failed_job.job_id,
                        source=failed_job.source,
                        trigger_type=failed_job.trigger_type,
                        status="failed",
                        attempt_count=failed_job.attempt_count,
                        details={"error": error_msg},
                    )
                )
                job_manager.ack_job(claimed.message_id, job=failed_job)
            except (JobQueueUnavailableError, KeyError):
                logger.warning(
                    "worker.job_fail_persist_failed",
                    extra={"job_id": running_job.job_id},
                )

            logger.exception(
                "worker.job.failed",
                extra={"job_id": running_job.job_id, "error": error_msg[:200]},
            )
            continue

        try:
            completed_job = job_manager.mark_completed(
                running_job.job_id,
                result,
                base_job=running_job,
            )
            _publish(
                ScrapeEvent(
                    event="job_completed",
                    message="Scrape job completed",
                    job_id=completed_job.job_id,
                    source=completed_job.source,
                    trigger_type=completed_job.trigger_type,
                    status="completed",
                    attempt_count=completed_job.attempt_count,
                    details={"result_status": result.get("status")},
                )
            )
            job_manager.ack_job(claimed.message_id, job=completed_job)
        except (JobQueueUnavailableError, KeyError):
            logger.warning(
                "worker.job_completion_persist_failed",
                extra={"job_id": running_job.job_id},
            )
            time.sleep(2)
            continue

        logger.info(
            "worker.job.completed",
            extra={"job_id": running_job.job_id, "status": result.get("status", "unknown")},
        )

    logger.info("worker.shutdown_complete")


if __name__ == "__main__":
    main()
