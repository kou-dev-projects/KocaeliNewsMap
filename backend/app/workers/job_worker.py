from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import logging
import signal
import sys
import time
from typing import Any

from app.scheduler.orchestrator import ScrapeCancellationRequested, ScrapeOrchestrator
from app.services.dataset_generation import (
    activate_generation,
    begin_refresh_generation,
    clear_pending_refresh_generation,
    get_dataset_generation_state,
)
from app.services.scrape_events import ScrapeEvent, get_scrape_event_publisher
from app.services.scrape_orchestrator import (
    cleanup_refresh_data,
    discard_refresh_generation,
)
from app.services.scrape_reset import reset_scraped_news_workspace
from app.settings import settings
from app.workers.job_manager import JobInfo, JobManager, JobQueueUnavailableError

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
_REFRESH_ALLOWED_SKIP_REASONS = frozenset(
    {
        "skipped_by_config",
        "unsupported_source",
    }
)
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
    """Fire-and-forget publish; never raises."""
    get_scrape_event_publisher().publish(event)


def _publish_job_event(
    *,
    job_id: str,
    trigger_type: str,
    event: str,
    message: str,
    status: str,
    source: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    _publish(
        ScrapeEvent(
            event=event,
            message=message,
            job_id=job_id,
            source=source,
            trigger_type=trigger_type,
            status=status,
            details=details,
        )
    )


def _build_progress_callback(*, job_id: str, trigger_type: str):
    def _progress_callback(payload: dict[str, Any]) -> None:
        _publish_job_event(
            job_id=job_id,
            trigger_type=trigger_type,
            event=str(payload.get("event") or "scrape_progress"),
            message=str(payload.get("message") or "Scrape progress update"),
            status=str(payload.get("status") or "running"),
            source=str(payload.get("source") or "") or None,
            details=payload.get("details") if isinstance(payload.get("details"), dict) else None,
        )

    return _progress_callback


def _reset_dataset_for_bootstrap(
    orchestrator: ScrapeOrchestrator,
    *,
    job_id: str,
    trigger_type: str,
    source: str | None,
) -> dict[str, Any]:
    reset_result = reset_scraped_news_workspace(orchestrator.database)

    details = {
        "deleted_counts": reset_result.deleted_counts,
        "total_deleted": reset_result.total_deleted,
    }
    _publish_job_event(
        job_id=job_id,
        trigger_type=trigger_type,
        event="dataset_reset",
        message="Bootstrap workspace cleared before scrape start",
        status="running",
        source=source,
        details=details,
    )
    return details


def _run_scrape_job(
    orchestrator: ScrapeOrchestrator,
    source: str | None,
    trigger_type: str,
    job_id: str,
    *,
    should_cancel=None,
) -> dict[str, Any]:
    refresh_generation: str | None = None
    progress_callback = _build_progress_callback(job_id=job_id, trigger_type=trigger_type)
    result: dict[str, Any] = {}

    if trigger_type == "bootstrap" and source is None:
        result["pre_scrape_reset"] = _reset_dataset_for_bootstrap(
            orchestrator,
            job_id=job_id,
            trigger_type=trigger_type,
            source=source,
        )
        if should_cancel is not None and should_cancel():
            raise ScrapeCancellationRequested("scrape_cancel_requested")

    if trigger_type == "refresh" and source is None:
        _publish_job_event(
            job_id=job_id,
            trigger_type=trigger_type,
            event="refresh_preserving_active_dataset",
            message=(
                "Active dataset remains visible while the refresh builds a new "
                "generation in the background"
            ),
            status="running",
            details={"visibility": "active_dataset_remains_visible"},
        )
        refresh_generation = begin_refresh_generation(orchestrator.database)
        _publish_job_event(
            job_id=job_id,
            trigger_type=trigger_type,
            event="refresh_generation_started",
            message="New dataset generation allocated for refresh",
            status="running",
            details={"generation": refresh_generation},
        )

    try:
        if source:
            crawl_result = orchestrator.crawl_source(
                source,
                trigger_type=trigger_type,
                progress_callback=progress_callback,
                should_cancel=should_cancel,
            )
        else:
            crawl_result = orchestrator.crawl_active_sources(
                trigger_type=trigger_type,
                dataset_generation=refresh_generation,
                progress_callback=progress_callback,
                should_cancel=should_cancel,
            )
    except Exception:
        if refresh_generation is not None:
            _abort_refresh_generation(orchestrator, refresh_generation)
        raise

    result.update(crawl_result)
    if source is None:
        _publish_job_event(
            job_id=job_id,
            trigger_type=trigger_type,
            event="crawl_summary_completed",
            message="Source crawl pass finished",
            status="completed",
            details={
                "status": result.get("status"),
                "active_sources": result.get("active_sources"),
                "processed_sources": result.get("processed_sources"),
                "failed_sources": result.get("failed_sources"),
                "skipped_sources": result.get("skipped_sources"),
            },
        )

    if refresh_generation is not None:
        result["dataset_generation"] = refresh_generation
        result["refresh_cleanup"] = _finalize_refresh_cleanup(
            orchestrator,
            summary=result,
            refresh_generation=refresh_generation,
            job_id=job_id,
        )

    drain_result = orchestrator.drain_pending_writes(batch_size=50)
    result["queue_drain"] = drain_result
    return result


def _collect_refresh_success(summary: dict[str, Any]) -> str | None:
    active_sources = int(summary.get("active_sources") or 0)
    processed_sources = int(summary.get("processed_sources") or 0)
    skipped_sources = int(summary.get("skipped_sources") or 0)
    skipped_session_reasons = summary.get("skipped_session_reasons")
    sessions = summary.get("sessions")

    if active_sources <= 0:
        return "no_active_sources"
    if skipped_sources > 0:
        if not isinstance(skipped_session_reasons, list):
            return "refresh_skipped_sources_present"

        normalized_skipped_reasons = [
            str(reason or "").strip()
            for reason in skipped_session_reasons
        ]
        if len(normalized_skipped_reasons) != skipped_sources:
            return "refresh_skipped_sources_present"
        if any(
            reason not in _REFRESH_ALLOWED_SKIP_REASONS
            for reason in normalized_skipped_reasons
        ):
            return "refresh_skipped_sources_present"

    eligible_sources = active_sources - skipped_sources
    if eligible_sources <= 0:
        return "no_refresh_eligible_sources"
    if processed_sources != eligible_sources:
        return "refresh_source_count_mismatch"
    if not isinstance(sessions, list) or len(sessions) != processed_sources:
        return "refresh_session_count_mismatch"

    for session in sessions:
        if not isinstance(session, dict):
            return "invalid_refresh_session_summary"
        if session.get("status") != "success":
            return "refresh_not_fully_successful"

    return None


def _abort_refresh_generation(
    orchestrator: ScrapeOrchestrator,
    refresh_generation: str,
) -> dict[str, Any]:
    cleanup_result = discard_refresh_generation(
        orchestrator.database,
        pending_generation=refresh_generation,
    )
    clear_pending_refresh_generation(
        orchestrator.database,
        expected_generation=refresh_generation,
    )
    return {
        "status": "discarded",
        "generation": cleanup_result.generation,
        "deleted_counts": cleanup_result.deleted_counts,
        "total_deleted": cleanup_result.total_deleted,
    }


def _has_active_generation(orchestrator: ScrapeOrchestrator) -> bool:
    state = get_dataset_generation_state(orchestrator.database)
    return bool(state.active_generation)


def _finalize_refresh_cleanup(
    orchestrator: ScrapeOrchestrator,
    summary: dict[str, Any],
    refresh_generation: str,
    job_id: str,
) -> dict[str, Any]:
    skip_reason = _collect_refresh_success(summary)
    if skip_reason is not None:
        if _has_active_generation(orchestrator):
            discard_result = _abort_refresh_generation(orchestrator, refresh_generation)
            _publish_job_event(
                job_id=job_id,
                trigger_type="refresh",
                event="refresh_cleanup_skipped",
                message=(
                    "Refresh candidate discarded to preserve the active dataset "
                    "after a partial run"
                ),
                status="skipped",
                details={
                    "reason": skip_reason,
                    "generation": refresh_generation,
                    "deleted_counts": discard_result["deleted_counts"],
                    "total_deleted": discard_result["total_deleted"],
                },
            )
            return {
                "status": "discarded",
                "reason": skip_reason,
                "generation": refresh_generation,
                "deleted_counts": discard_result["deleted_counts"],
                "total_deleted": discard_result["total_deleted"],
            }

        _publish_job_event(
            job_id=job_id,
            trigger_type="refresh",
            event="refresh_partial_cutover_started",
            message=(
                "Refresh had partial source failures and no active dataset was "
                "available. Promoting partial generation to avoid an empty feed"
            ),
            status="running",
            details={
                "reason": skip_reason,
                "generation": refresh_generation,
            },
        )

        try:
            activate_generation(orchestrator.database, refresh_generation)
            cleanup_result = cleanup_refresh_data(
                orchestrator.database,
                active_generation=refresh_generation,
            )
        except Exception as exc:
            error_message = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "worker.refresh_partial_cutover.failed",
                extra={"error": error_message[:200]},
            )
            discard_result = _abort_refresh_generation(orchestrator, refresh_generation)
            _publish_job_event(
                job_id=job_id,
                trigger_type="refresh",
                event="refresh_cleanup_skipped",
                message=(
                    "Refresh candidate discarded because partial cutover fallback "
                    "failed"
                ),
                status="skipped",
                details={
                    "reason": skip_reason,
                    "generation": refresh_generation,
                    "error": error_message,
                    "deleted_counts": discard_result["deleted_counts"],
                    "total_deleted": discard_result["total_deleted"],
                },
            )
            return {
                "status": "discarded",
                "reason": skip_reason,
                "generation": refresh_generation,
                "error": error_message,
                "deleted_counts": discard_result["deleted_counts"],
                "total_deleted": discard_result["total_deleted"],
            }

        _publish_job_event(
            job_id=job_id,
            trigger_type="refresh",
            event="refresh_partial_cutover_completed",
            message=(
                "Partial refresh generation activated because no active dataset "
                "was available"
            ),
            status="completed",
            details={
                "reason": skip_reason,
                "generation": cleanup_result.generation,
                "deleted_counts": cleanup_result.deleted_counts,
                "total_deleted": cleanup_result.total_deleted,
            },
        )
        return {
            "status": "completed_with_partial",
            "reason": skip_reason,
            "generation": cleanup_result.generation,
            "deleted_counts": cleanup_result.deleted_counts,
            "total_deleted": cleanup_result.total_deleted,
        }

    try:
        _publish_job_event(
            job_id=job_id,
            trigger_type="refresh",
            event="refresh_cutover_started",
            message=(
                "Refresh crawl finished. Cutover is activating the new dataset "
                "generation now"
            ),
            status="running",
            details={"generation": refresh_generation},
        )
        activate_generation(orchestrator.database, refresh_generation)
        cleanup_result = cleanup_refresh_data(
            orchestrator.database,
            active_generation=refresh_generation,
        )
    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        logger.exception("worker.refresh_cleanup.failed", extra={"error": error_message[:200]})
        _publish_job_event(
            job_id=job_id,
            trigger_type="refresh",
            event="refresh_cleanup_failed",
            message="Refresh cleanup failed after crawl completion",
            status="error",
            details={"error": error_message},
        )
        return {
            "status": "failed",
            "error": error_message,
        }

    _publish_job_event(
        job_id=job_id,
        trigger_type="refresh",
        event="refresh_cleanup_completed",
        message=(
            "Refresh cutover activated the new dataset generation and removed "
            "stale news records"
        ),
        status="completed",
        details={
            "generation": cleanup_result.generation,
            "deleted_counts": cleanup_result.deleted_counts,
            "total_deleted": cleanup_result.total_deleted,
        },
    )
    return {
        "status": "completed",
        "generation": cleanup_result.generation,
        "deleted_counts": cleanup_result.deleted_counts,
        "total_deleted": cleanup_result.total_deleted,
    }


def _execute_job_with_heartbeat(
    job_manager: JobManager,
    orchestrator: ScrapeOrchestrator,
    claimed_message_id: str,
    running_job: JobInfo,
) -> tuple[dict[str, Any], JobInfo]:
    heartbeat_seconds = max(settings.job_heartbeat_seconds, 1)
    current_job = running_job

    def _should_cancel() -> bool:
        try:
            return job_manager.is_cancel_requested(current_job.job_id)
        except JobQueueUnavailableError:
            logger.warning(
                "worker.job_cancel_state_unavailable",
                extra={"job_id": current_job.job_id},
            )
            return False

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            _run_scrape_job,
            orchestrator,
            current_job.source,
            current_job.trigger_type,
            current_job.job_id,
            should_cancel=_should_cancel,
        )

        while True:
            try:
                return future.result(timeout=heartbeat_seconds), current_job
            except FutureTimeoutError:
                if _should_cancel():
                    raise ScrapeCancellationRequested("scrape_cancel_requested")
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

        if job.status in {"completed", "failed", "cancelled"}:
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
        except ScrapeCancellationRequested as exc:
            try:
                cancelled_job = job_manager.mark_cancelled(
                    running_job.job_id,
                    str(exc),
                    base_job=running_job,
                )
                _publish(
                    ScrapeEvent(
                        event="job_cancelled",
                        message="Scrape job stopped by user request",
                        job_id=cancelled_job.job_id,
                        source=cancelled_job.source,
                        trigger_type=cancelled_job.trigger_type,
                        status="cancelled",
                        attempt_count=cancelled_job.attempt_count,
                        details={"error": str(exc)},
                    )
                )
                job_manager.ack_job(claimed.message_id, job=cancelled_job)
            except (JobQueueUnavailableError, KeyError):
                logger.warning(
                    "worker.job_cancel_persist_failed",
                    extra={"job_id": running_job.job_id},
                )
                time.sleep(2)
                continue

            logger.info(
                "worker.job.cancelled",
                extra={"job_id": running_job.job_id},
            )
            continue
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

        if job.cancel_requested and job.status == "pending":
            try:
                cancelled_job = job_manager.mark_cancelled(
                    job.job_id,
                    "scrape_cancel_requested",
                    base_job=job,
                )
                _publish(
                    ScrapeEvent(
                        event="job_cancelled",
                        message="Scrape job stopped before execution started",
                        job_id=cancelled_job.job_id,
                        source=cancelled_job.source,
                        trigger_type=cancelled_job.trigger_type,
                        status="cancelled",
                        attempt_count=cancelled_job.attempt_count,
                        details={"error": "scrape_cancel_requested"},
                    )
                )
                job_manager.ack_job(claimed.message_id, job=cancelled_job)
            except (JobQueueUnavailableError, KeyError):
                logger.warning("worker.job_cancel_persist_failed", extra={"job_id": job.job_id})
                time.sleep(2)
                continue
            continue

        result_status = str(result.get("status") or "success")
        if result_status == "failed":
            failed_sources = int(result.get("failed_sources") or 0)
            error_msg = (
                f"Scrape crawl failed: {failed_sources} source(s) failed and no successful source completed"
            )
            try:
                failed_job = job_manager.mark_failed(
                    running_job.job_id,
                    error_msg,
                    base_job=running_job,
                )
                _publish(
                    ScrapeEvent(
                        event="job_failed",
                        message="Scrape job failed after source crawl errors",
                        job_id=failed_job.job_id,
                        source=failed_job.source,
                        trigger_type=failed_job.trigger_type,
                        status="failed",
                        attempt_count=failed_job.attempt_count,
                        details={
                            "error": error_msg,
                            "result_status": result_status,
                            "failed_sources": failed_sources,
                        },
                    )
                )
                job_manager.ack_job(claimed.message_id, job=failed_job)
            except (JobQueueUnavailableError, KeyError):
                logger.warning(
                    "worker.job_fail_persist_failed",
                    extra={"job_id": running_job.job_id},
                )
                time.sleep(2)
                continue

            logger.warning(
                "worker.job.failed_after_crawl",
                extra={"job_id": running_job.job_id, "failed_sources": failed_sources},
            )
            continue

        try:
            completed_job = job_manager.mark_completed(
                running_job.job_id,
                result,
                base_job=running_job,
            )
            completion_event = "job_completed"
            completion_message = "Scrape job completed"
            if result_status == "completed_with_errors":
                completion_event = "job_partial"
                completion_message = "Scrape job completed with source failures"
            _publish(
                ScrapeEvent(
                    event=completion_event,
                    message=completion_message,
                    job_id=completed_job.job_id,
                    source=completed_job.source,
                    trigger_type=completed_job.trigger_type,
                    status="completed",
                    attempt_count=completed_job.attempt_count,
                    details={
                        "result_status": result_status,
                        "failed_sources": result.get("failed_sources"),
                        "processed_sources": result.get("processed_sources"),
                    },
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
