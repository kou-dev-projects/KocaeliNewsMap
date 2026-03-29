from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from .schemas import LeaseInfo

logger = logging.getLogger(__name__)

_LEASE_KEY_PREFIX = "pulse:lease:v1"

try:
    import redis as redis_lib

    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False


class SourceLease:
    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        self._redis_url = redis_url
        self._ttl = ttl_seconds
        self._client: Optional["redis_lib.Redis"] = None
        self._connect()

    def _connect(self) -> Optional["redis_lib.Redis"]:
        if not _REDIS_AVAILABLE:
            logger.warning("mcp.lease.unavailable", extra={"reason": "redis_py_missing"})
            self._client = None
            return None

        try:
            self._client = redis_lib.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=1,
            )
            self._client.ping()
            logger.info("mcp.lease.ready", extra={"ttl_seconds": self._ttl})
        except Exception as exc:
            logger.warning("mcp.lease.unavailable", extra={"reason": type(exc).__name__})
            self._client = None
        return self._client

    def _get_client(self) -> Optional["redis_lib.Redis"]:
        if self._client is None:
            return self._connect()
        return self._client

    def _handle_error(self, exc: Exception, event: str) -> None:
        logger.warning(event, extra={"error": type(exc).__name__})
        self._client = None

    def acquire(self, source: str, worker_id: str) -> bool:
        client = self._get_client()
        if client is None:
            logger.warning("mcp.lease.redis_unavailable", extra={"source": source})
            return False

        key = self._key(source)
        try:
            acquired = client.set(
                key,
                worker_id,
                ex=self._ttl,
                nx=True,
            )
            current_holder = None if acquired else client.get(key)
        except Exception as exc:
            self._handle_error(exc, "mcp.lease.acquire_failed")
            return False

        if acquired:
            logger.info(
                "mcp.lease.acquired",
                extra={"source": source, "worker_id": worker_id, "ttl": self._ttl},
            )
        else:
            logger.info(
                "mcp.lease.already_held",
                extra={"source": source, "held_by": current_holder},
            )

        return bool(acquired)

    def release(self, source: str, worker_id: str) -> bool:
        client = self._get_client()
        if client is None:
            return False

        key = self._key(source)
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            released = bool(client.eval(lua_script, 1, key, worker_id))
        except Exception as exc:
            self._handle_error(exc, "mcp.lease.release_failed")
            return False

        logger.info(
            "mcp.lease.released" if released else "mcp.lease.release_failed",
            extra={"source": source, "worker_id": worker_id},
        )
        return released

    def get_info(self, source: str) -> Optional[LeaseInfo]:
        client = self._get_client()
        if client is None:
            return None

        key = self._key(source)
        try:
            pipe = client.pipeline()
            pipe.get(key)
            pipe.ttl(key)
            holder, ttl = pipe.execute()
        except Exception as exc:
            self._handle_error(exc, "mcp.lease.info_failed")
            return None

        if not holder:
            return None

        return LeaseInfo(
            source=source,
            worker_id=holder,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=max(ttl, 0)),
            ttl_seconds=max(ttl, 0),
        )

    def is_held(self, source: str) -> bool:
        client = self._get_client()
        if client is None:
            return False

        try:
            return bool(client.exists(self._key(source)))
        except Exception as exc:
            self._handle_error(exc, "mcp.lease.exists_failed")
            return False

    def _key(self, source: str) -> str:
        return f"{_LEASE_KEY_PREFIX}:{source}"
