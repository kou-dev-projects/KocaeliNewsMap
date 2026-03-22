from __future__ import annotations
import logging

from pymongo import MongoClient

from .config import MCPConfig, load_mcp_config
from .dead_letter import DeadLetterStore
from .idempotency import IdempotencyStore
from .lease import SourceLease
from .queue import WriteQueue
from .tools.news_tools import make_news_tools
from .write_service import NewsWriteService

logger = logging.getLogger(__name__)


class MCPServer:

    def __init__(self, config: MCPConfig | None = None) -> None:
        cfg = config or load_mcp_config()

        self._mongo = MongoClient(
            cfg.mongo_url,
            serverSelectionTimeoutMS=2000,
        )

        try:
            self._mongo.admin.command("ping")
            logger.info(
                "mcp.mongo.ready",
                extra={"mongo_db": cfg.mongo_db},
            )
        except Exception as exc:
            logger.warning(
                "mcp.mongo.unavailable",
                extra={"error": type(exc).__name__, "mongo_db": cfg.mongo_db},
            )
           
        self._idempotency = IdempotencyStore(
            cfg.redis_url, cfg.idempotency_ttl_seconds
        )
        self._lease = SourceLease(cfg.redis_url, cfg.lease_ttl_seconds)
        self._queue = WriteQueue(cfg.max_queue_size, cfg.max_queue_retries)
        self._dead_letter = DeadLetterStore()
        self._write_service = NewsWriteService(
            idempotency=self._idempotency,
            queue=self._queue,
            dead_letter=self._dead_letter,
            config=cfg,
            mongo_client=self._mongo,
        )

        self.tools = make_news_tools(self._write_service, self._lease)
        logger.info(
            "mcp.server.ready",
            extra={"tools": list(self.tools.keys())},
        )

    def call(self, tool_name: str, **kwargs):
        if tool_name not in self.tools:
            raise ValueError(f"Bilinmeyen tool: {tool_name!r}")
        return self.tools[tool_name](**kwargs)
