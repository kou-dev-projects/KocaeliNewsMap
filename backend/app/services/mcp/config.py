from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from app.settings import settings


@dataclass(frozen=True)
class MCPConfig:

    redis_url: str
    mongo_url: str
    mongo_db: str
    lease_ttl_seconds: int
    idempotency_ttl_seconds: int
    max_queue_size: int
    max_queue_retries: int
    fail_closed: bool
    worker_id: Optional[str]


def load_mcp_config() -> MCPConfig:
    import socket

    worker_id = settings.worker_id or socket.gethostname()

    return MCPConfig(
        redis_url=settings.redis_url,
        mongo_url=settings.mongo_url,
        mongo_db=settings.mongo_db,
        lease_ttl_seconds=settings.mcp_lease_ttl,
        idempotency_ttl_seconds=settings.mcp_idempotency_ttl,
        max_queue_size=settings.mcp_queue_size,
        max_queue_retries=settings.mcp_max_retries,
        fail_closed=settings.mcp_fail_closed,
        worker_id=worker_id,
    )