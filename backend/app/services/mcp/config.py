from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


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
    mcp_host: str
    mcp_port: int
    worker_id: Optional[str]


def load_mcp_config() -> MCPConfig:
    import socket
    return MCPConfig(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        mongo_url=os.getenv("MONGO_URL", "mongodb://localhost:27017"),
        mongo_db=os.getenv("MONGO_DB", "kocaeli_news"),
        lease_ttl_seconds=int(os.getenv("MCP_LEASE_TTL", "300")),
        idempotency_ttl_seconds=int(os.getenv("MCP_IDEMPOTENCY_TTL", "86400")),
        max_queue_size=int(os.getenv("MCP_QUEUE_SIZE", "1000")),
        max_queue_retries=int(os.getenv("MCP_MAX_RETRIES", "3")),
        fail_closed=os.getenv("MCP_FAIL_CLOSED", "true").lower() == "true",
        mcp_host=os.getenv("MCP_HOST", "0.0.0.0"),
        mcp_port=int(os.getenv("MCP_PORT", "8001")),
        worker_id=os.getenv("WORKER_ID", socket.gethostname()),
    )