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
        self._ttl = ttl_seconds
        self._client: Optional["redis_lib.Redis"] = None

        if not _REDIS_AVAILABLE:
            logger.warning(
                "mcp.lease.unavailable",
                extra={"reason": "redis-py kurulu değil"},
            )
            return

        try:
            self._client = redis_lib.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=1,
            )
            self._client.ping()
            logger.info("mcp.lease.ready", extra={"ttl_seconds": ttl_seconds})
        except Exception as exc:
            logger.warning(
                "mcp.lease.unavailable",
                extra={"reason": type(exc).__name__},
            )
            self._client = None

    def acquire(self, source: str, worker_id: str) -> bool:
       
        if not self._client:
            # Redis yoksa kilit alınamaz — fail_closed modda
            # caller bu durumu handle eder
            logger.warning(
                "mcp.lease.redis_unavailable",
                extra={"source": source},
            )
            return False

        key = self._key(source)
        acquired = self._client.set(
            key,
            worker_id,
            ex=self._ttl,
            nx=True,   # Only set if Not eXists
        )

        if acquired:
            logger.info(
                "mcp.lease.acquired",
                extra={"source": source, "worker_id": worker_id, "ttl": self._ttl},
            )
        else:
            current_holder = self._client.get(key)
            logger.info(
                "mcp.lease.already_held",
                extra={"source": source, "held_by": current_holder},
            )

        return bool(acquired)

    def release(self, source: str, worker_id: str) -> bool:
        """
        Kilidi sadece sahibi bırakabilir.
        Lua script ile atomic check-and-delete.
        """
        if not self._client:
            return False

        key = self._key(source)
        # Atomic: başkasının kilidini silme
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = self._client.eval(lua_script, 1, key, worker_id)
        released = bool(result)

        logger.info(
            "mcp.lease.released" if released else "mcp.lease.release_failed",
            extra={"source": source, "worker_id": worker_id},
        )
        return released

    def get_info(self, source: str) -> Optional[LeaseInfo]:
        """Mevcut kilit bilgisi — debug ve monitoring için."""
        if not self._client:
            return None

        key = self._key(source)
        pipe = self._client.pipeline()
        pipe.get(key)
        pipe.ttl(key)
        holder, ttl = pipe.execute()

        if not holder:
            return None

        return LeaseInfo(
            source=source,
            worker_id=holder,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=max(ttl, 0)),
            ttl_seconds=max(ttl, 0),
        )

    def is_held(self, source: str) -> bool:
        if not self._client:
            return False
        return bool(self._client.exists(self._key(source)))

    def _key(self, source: str) -> str:
        return f"{_LEASE_KEY_PREFIX}:{source}"