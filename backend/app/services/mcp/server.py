from __future__ import annotations
import logging

from pymongo import MongoClient

from .config import MCPConfig, load_mcp_config
from .dead_letter import DeadLetterStore
from .idempotency import IdempotencyStore
from .lease import SourceLease
from .queue import WriteQueue
from .write_service import NewsWriteService

logger = logging.getLogger(__name__)

_MONGO_CLIENTS: dict[str, MongoClient] = {}


def _get_shared_mongo_client(mongo_url: str) -> MongoClient:
    client = _MONGO_CLIENTS.get(mongo_url)
    if client is None:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        _MONGO_CLIENTS[mongo_url] = client
    return client


def create_write_services(
    config: MCPConfig | None = None,
) -> tuple[NewsWriteService, SourceLease]:
    cfg = config or load_mcp_config()

    if config is None:
        mongo = _get_shared_mongo_client(cfg.mongo_url)
    else:
        mongo = MongoClient(cfg.mongo_url, serverSelectionTimeoutMS=2000)

    try:
        mongo.admin.command("ping")
        logger.info(
            "mcp.mongo.ready",
            extra={"mongo_db": cfg.mongo_db},
        )
    except Exception as exc:
        logger.warning(
            "mcp.mongo.unavailable",
            extra={"error": type(exc).__name__, "mongo_db": cfg.mongo_db},
        )

    idempotency = IdempotencyStore(cfg.redis_url, cfg.idempotency_ttl_seconds)
    lease = SourceLease(cfg.redis_url, cfg.lease_ttl_seconds)
    queue = WriteQueue(
        cfg.max_queue_size,
        cfg.max_queue_retries,
        redis_url=cfg.redis_url,
        allow_memory_fallback=False,
    )
    dead_letter = DeadLetterStore(redis_url=cfg.redis_url)
    write_service = NewsWriteService(
        idempotency=idempotency,
        queue=queue,
        dead_letter=dead_letter,
        config=cfg,
        mongo_client=mongo,
    )

    logger.info("mcp.services.ready")
    return write_service, lease
