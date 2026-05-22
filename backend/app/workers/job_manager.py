from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from socket import gethostname
from typing import Any
from uuid import uuid4

import redis

from app.settings import settings

logger = logging.getLogger(__name__)

_JOB_KEY_PREFIX = "pulse:jobs:v1"
_JOB_STREAM_KEY = "pulse:jobs:stream:v1"
_JOB_GROUP = "pulse:jobs:workers:v1"
_SCHEDULED_LOCK_KEY = "pulse:jobs:scheduled:v1"


class JobQueueUnavailableError(RuntimeError):
    pass


class ScheduledJobAlreadyQueuedError(RuntimeError):
    pass


@dataclass
class JobInfo:
    job_id: str
    status: str  # pending | running | completed | failed | cancelled
    source: str | None
    trigger_type: str
    created_at: float
    started_at: float | None = None
    completed_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    attempt_count: int = 0
    last_heartbeat_at: float | None = None
    cancel_requested: bool = False
    cancel_requested_at: float | None = None


@dataclass(frozen=True)
class ClaimedJob:
    message_id: str
    job: JobInfo


class JobManager:
    def __init__(
        self,
        redis_url: str | None = None,
        *,
        consumer_name: str | None = None,
        job_ttl_seconds: int | None = None,
        claim_idle_seconds: int | None = None,
        scheduled_lock_ttl_seconds: int | None = None,
    ) -> None:
        self._redis_url = redis_url or settings.redis_url
        if consumer_name is not None:
            self._consumer_name = consumer_name
        else:
            base_consumer_name = settings.worker_id or "worker"
            self._consumer_name = (
                f"{base_consumer_name}:{gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
            )
        self._job_ttl_seconds = max(job_ttl_seconds or settings.job_ttl_seconds, 60)
        self._claim_idle_seconds = max(claim_idle_seconds or settings.job_claim_idle_seconds, 1)
        self._scheduled_lock_ttl_seconds = max(
            scheduled_lock_ttl_seconds or settings.scheduled_job_lock_ttl_seconds,
            60,
        )
        self._redis: redis.Redis | None = None
        self._group_ready = False
        self._connect()

    def _connect(self) -> redis.Redis | None:
        try:
            client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=None,
            )
            client.ping()
            self._redis = client
            self._group_ready = False
            logger.info("job_manager.redis.ready")
        except Exception as exc:
            logger.warning(
                "job_manager.redis.unavailable",
                extra={"error": type(exc).__name__},
            )
            self._redis = None
            self._group_ready = False
        return self._redis

    def _get_redis(self) -> redis.Redis | None:
        if self._redis is None:
            return self._connect()
        return self._redis

    def _require_redis(self) -> redis.Redis:
        client = self._get_redis()
        if client is None:
            raise JobQueueUnavailableError("job_manager: Redis is not available")
        return client

    def _handle_redis_error(self, exc: Exception, event: str) -> None:
        logger.warning(
            event,
            extra={"error": type(exc).__name__},
        )
        self._redis = None
        self._group_ready = False

    def _ensure_group(self, client: redis.Redis) -> None:
        if self._group_ready:
            return

        try:
            client.xgroup_create(
                name=_JOB_STREAM_KEY,
                groupname=_JOB_GROUP,
                id="0-0",
                mkstream=True,
            )
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                self._handle_redis_error(exc, "job_manager.redis.group_create_failed")
                raise JobQueueUnavailableError("job_manager: stream group unavailable") from exc

        self._group_ready = True

    @property
    def available(self) -> bool:
        try:
            client = self._require_redis()
            client.ping()
            self._ensure_group(client)
            return True
        except Exception:
            return False

    def submit_job(
        self,
        source: str | None = None,
        trigger_type: str = "manual",
    ) -> str:
        client = self._require_redis()
        self._ensure_group(client)

        job_id = uuid4().hex[:16]
        scheduled_lock_acquired = False

        if trigger_type == "scheduled" and source is None:
            scheduled_lock_acquired = self._acquire_scheduled_lock(client, job_id)
            if not scheduled_lock_acquired:
                raise ScheduledJobAlreadyQueuedError("scheduled_crawl_already_queued")

        job = JobInfo(
            job_id=job_id,
            status="pending",
            source=source,
            trigger_type=trigger_type,
            created_at=time.time(),
        )

        try:
            pipe = client.pipeline(transaction=True)
            pipe.setex(self._job_key(job_id), self._job_ttl_seconds, json.dumps(asdict(job)))
            pipe.xadd(_JOB_STREAM_KEY, self._stream_fields(job))
            pipe.execute()
        except Exception as exc:
            if scheduled_lock_acquired:
                self._release_scheduled_lock(client, job_id, suppress_errors=True)
            self._handle_redis_error(exc, "job_manager.job.submit_failed")
            raise JobQueueUnavailableError("job_manager: failed to submit job") from exc

        logger.info(
            "job_manager.job.submitted",
            extra={"job_id": job_id, "source": source, "trigger_type": trigger_type},
        )
        return job_id

    def submit_scheduled_crawl_job(self) -> str | None:
        try:
            return self.submit_job(source=None, trigger_type="scheduled")
        except ScheduledJobAlreadyQueuedError:
            return None

    def get_job(self, job_id: str) -> JobInfo | None:
        client = self._require_redis()
        try:
            raw = client.get(self._job_key(job_id))
        except Exception as exc:
            self._handle_redis_error(exc, "job_manager.job.fetch_failed")
            raise JobQueueUnavailableError("job_manager: failed to fetch job") from exc

        if raw is None:
            return None

        return JobInfo(**json.loads(raw))

    def request_cancel(self, job_id: str, *, base_job: JobInfo | None = None) -> JobInfo:
        requested_at = time.time()
        return self._update_job(
            job_id,
            base_job=base_job,
            cancel_requested=True,
            cancel_requested_at=requested_at,
        )

    def is_cancel_requested(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if job is None:
            return False
        return bool(job.cancel_requested)

    def find_latest_active_job(self) -> JobInfo | None:
        client = self._require_redis()
        latest_job: JobInfo | None = None
        now = time.time()

        try:
            for key in client.scan_iter(match=f"{_JOB_KEY_PREFIX}:*"):
                raw = client.get(key)
                if raw is None:
                    continue

                candidate = JobInfo(**json.loads(raw))
                if candidate.status not in {"pending", "running"}:
                    continue

                if self._is_stale_active_job(candidate, now=now):
                    continue

                if latest_job is None or self._activity_timestamp(candidate) >= self._activity_timestamp(
                    latest_job
                ):
                    latest_job = candidate
        except Exception as exc:
            self._handle_redis_error(exc, "job_manager.job.scan_active_failed")
            raise JobQueueUnavailableError("job_manager: failed to scan active jobs") from exc

        return latest_job

    def _is_stale_active_job(self, job: JobInfo, *, now: float) -> bool:
        stale_after_seconds = max(self._claim_idle_seconds, settings.job_heartbeat_seconds * 4, 120)
        activity_at = self._activity_timestamp(job)
        return (now - activity_at) > stale_after_seconds

    @staticmethod
    def _activity_timestamp(job: JobInfo) -> float:
        return float(job.last_heartbeat_at or job.started_at or job.created_at)

    def dequeue_job(self, timeout: int = 5) -> ClaimedJob | None:
        client = self._require_redis()
        self._ensure_group(client)

        stale_job = self._claim_stale_job(client)
        if stale_job is not None:
            return stale_job

        try:
            entries = client.xreadgroup(
                groupname=_JOB_GROUP,
                consumername=self._consumer_name,
                streams={_JOB_STREAM_KEY: ">"},
                count=1,
                block=max(timeout, 1) * 1000,
            )
        except Exception as exc:
            self._handle_redis_error(exc, "job_manager.job.dequeue_failed")
            raise JobQueueUnavailableError("job_manager: failed to dequeue job") from exc

        return self._parse_stream_entries(entries)

    def mark_running(self, job_id: str, *, base_job: JobInfo | None = None) -> JobInfo:
        return self._update_job(
            job_id,
            base_job=base_job,
            status="running",
            started_at=time.time(),
            completed_at=None,
            result=None,
            error=None,
            last_heartbeat_at=time.time(),
        )

    def mark_completed(
        self,
        job_id: str,
        result: dict[str, Any],
        *,
        base_job: JobInfo | None = None,
    ) -> JobInfo:
        return self._update_job(
            job_id,
            base_job=base_job,
            status="completed",
            completed_at=time.time(),
            result=result,
            error=None,
            last_heartbeat_at=time.time(),
        )

    def mark_failed(self, job_id: str, error: str, *, base_job: JobInfo | None = None) -> JobInfo:
        return self._update_job(
            job_id,
            base_job=base_job,
            status="failed",
            completed_at=time.time(),
            error=error[:500],
            last_heartbeat_at=time.time(),
        )

    def mark_cancelled(
        self,
        job_id: str,
        reason: str,
        *,
        base_job: JobInfo | None = None,
    ) -> JobInfo:
        return self._update_job(
            job_id,
            base_job=base_job,
            status="cancelled",
            completed_at=time.time(),
            error=reason[:500],
            last_heartbeat_at=time.time(),
            cancel_requested=True,
            cancel_requested_at=time.time(),
        )

    def heartbeat_job(
        self,
        message_id: str,
        job_id: str,
        *,
        base_job: JobInfo | None = None,
    ) -> JobInfo:
        client = self._require_redis()
        heartbeat_at = time.time()

        try:
            self._touch_claim(client, message_id)
        except Exception as exc:
            self._handle_redis_error(exc, "job_manager.job.heartbeat_touch_failed")
            raise JobQueueUnavailableError("job_manager: failed to heartbeat job") from exc

        return self._update_job(
            job_id,
            base_job=base_job,
            status="running",
            last_heartbeat_at=heartbeat_at,
        )

    def retry_job(self, message_id: str, job: JobInfo, error: str) -> JobInfo:
        client = self._require_redis()
        retry_job = JobInfo(
            job_id=job.job_id,
            status="pending",
            source=job.source,
            trigger_type=job.trigger_type,
            created_at=job.created_at,
            started_at=None,
            completed_at=None,
            result=None,
            error=error[:500],
            attempt_count=job.attempt_count + 1,
            last_heartbeat_at=None,
        )

        try:
            pipe = client.pipeline(transaction=True)
            pipe.setex(
                self._job_key(retry_job.job_id),
                self._job_ttl_seconds,
                json.dumps(asdict(retry_job)),
            )
            pipe.xack(_JOB_STREAM_KEY, _JOB_GROUP, message_id)
            pipe.xdel(_JOB_STREAM_KEY, message_id)
            pipe.xadd(_JOB_STREAM_KEY, self._stream_fields(retry_job))
            pipe.execute()
        except Exception as exc:
            self._handle_redis_error(exc, "job_manager.job.retry_failed")
            raise JobQueueUnavailableError("job_manager: failed to retry job") from exc

        return retry_job

    def ack_job(self, message_id: str, *, job: JobInfo | None = None) -> None:
        client = self._require_redis()
        try:
            pipe = client.pipeline(transaction=True)
            pipe.xack(_JOB_STREAM_KEY, _JOB_GROUP, message_id)
            pipe.xdel(_JOB_STREAM_KEY, message_id)
            pipe.execute()
        except Exception as exc:
            self._handle_redis_error(exc, "job_manager.job.ack_failed")
            raise JobQueueUnavailableError("job_manager: failed to ack job") from exc

        if job is not None and job.trigger_type == "scheduled" and job.source is None:
            self._release_scheduled_lock(client, job.job_id, suppress_errors=True)

    def _update_job(self, job_id: str, *, base_job: JobInfo | None = None, **fields: Any) -> JobInfo:
        client = self._require_redis()
        key = self._job_key(job_id)

        try:
            raw = client.get(key)
        except Exception as exc:
            self._handle_redis_error(exc, "job_manager.job.update_read_failed")
            raise JobQueueUnavailableError("job_manager: failed to read job state") from exc

        if raw is None:
            if base_job is None:
                raise KeyError(f"missing_job_state: {job_id}")
            data = asdict(base_job)
        else:
            data = json.loads(raw)

        data.update(fields)

        try:
            client.setex(key, self._job_ttl_seconds, json.dumps(data))
        except Exception as exc:
            self._handle_redis_error(exc, "job_manager.job.update_write_failed")
            raise JobQueueUnavailableError("job_manager: failed to write job state") from exc

        return JobInfo(**data)

    def _claim_stale_job(self, client: redis.Redis) -> ClaimedJob | None:
        try:
            try:
                result = client.xautoclaim(
                    _JOB_STREAM_KEY,
                    _JOB_GROUP,
                    self._consumer_name,
                    self._claim_idle_seconds * 1000,
                    "0-0",
                    count=1,
                )
            except TypeError:
                result = client.xautoclaim(
                    _JOB_STREAM_KEY,
                    _JOB_GROUP,
                    self._consumer_name,
                    self._claim_idle_seconds * 1000,
                    "0-0",
                )
        except Exception as exc:
            self._handle_redis_error(exc, "job_manager.job.autoclaim_failed")
            raise JobQueueUnavailableError("job_manager: failed to claim stale jobs") from exc

        entries: list[tuple[str, dict[str, Any]]] = []
        if isinstance(result, tuple):
            if len(result) >= 2:
                entries = result[1] or []
        elif isinstance(result, list) and len(result) >= 2:
            entries = result[1] or []

        if not entries:
            return None

        return self._parse_claimed_entry(entries[0])

    def _touch_claim(self, client: redis.Redis, message_id: str) -> None:
        try:
            client.xclaim(
                _JOB_STREAM_KEY,
                _JOB_GROUP,
                self._consumer_name,
                0,
                [message_id],
            )
        except TypeError:
            client.xclaim(
                name=_JOB_STREAM_KEY,
                groupname=_JOB_GROUP,
                consumername=self._consumer_name,
                min_idle_time=0,
                message_ids=[message_id],
            )

    def _parse_stream_entries(self, entries: Any) -> ClaimedJob | None:
        if not entries:
            return None

        _stream_name, stream_entries = entries[0]
        if not stream_entries:
            return None

        return self._parse_claimed_entry(stream_entries[0])

    def _parse_claimed_entry(self, entry: tuple[str, dict[str, Any]]) -> ClaimedJob:
        message_id, payload = entry
        source = payload.get("source") or None
        created_at = payload.get("created_at")

        job = JobInfo(
            job_id=payload["job_id"],
            status="pending",
            source=source,
            trigger_type=payload.get("trigger_type", "manual"),
            created_at=float(created_at) if created_at is not None else time.time(),
            attempt_count=int(payload.get("attempt_count", 0) or 0),
        )
        return ClaimedJob(message_id=message_id, job=job)

    def _acquire_scheduled_lock(self, client: redis.Redis, job_id: str) -> bool:
        try:
            acquired = client.set(
                _SCHEDULED_LOCK_KEY,
                job_id,
                ex=self._scheduled_lock_ttl_seconds,
                nx=True,
            )
        except Exception as exc:
            self._handle_redis_error(exc, "job_manager.job.lock_acquire_failed")
            raise JobQueueUnavailableError("job_manager: failed to acquire scheduled lock") from exc

        return bool(acquired)

    def _release_scheduled_lock(
        self,
        client: redis.Redis,
        job_id: str,
        *,
        suppress_errors: bool,
    ) -> None:
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            client.eval(lua_script, 1, _SCHEDULED_LOCK_KEY, job_id)
        except Exception as exc:
            if suppress_errors:
                logger.warning(
                    "job_manager.job.lock_release_failed",
                    extra={"error": type(exc).__name__, "job_id": job_id},
                )
                return
            self._handle_redis_error(exc, "job_manager.job.lock_release_failed")
            raise JobQueueUnavailableError("job_manager: failed to release scheduled lock") from exc

    @staticmethod
    def _stream_fields(job: JobInfo) -> dict[str, str]:
        return {
            "job_id": job.job_id,
            "source": job.source or "",
            "trigger_type": job.trigger_type,
            "created_at": str(job.created_at),
            "attempt_count": str(job.attempt_count),
        }

    @staticmethod
    def _job_key(job_id: str) -> str:
        return f"{_JOB_KEY_PREFIX}:{job_id}"
