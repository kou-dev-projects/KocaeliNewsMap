"""
NewsWriteService — persistence boundary.

Tüm scraper yazmaları buradan geçer.
Doğrudan MongoDB erişimi yoktur scraper'larda.

Yazma akışı:
  1) Idempotency check (Redis) → zaten işlendi mi?
  2) MongoDB upsert (url unique index) → insert veya duplicate merge
  3) Idempotency key kaydet
  4) WriteResult döndür

Fail-closed:
  MongoDB bağlantısı yoksa → queue'ya al
  Queue doluysa → dead-letter
  Her iki durumda da scraper'a WriteStatus.QUEUED veya
  WriteStatus.DEAD_LETTERED döner.
  Scraper asla doğrudan DB'ye yazmaz.
"""
from __future__ import annotations
import logging
from typing import Optional

from .config import MCPConfig
from .dead_letter import DeadLetterStore
from .idempotency import IdempotencyStore
from .queue import WriteQueue, QueueItem
from .schemas import NewsWriteRequest, WriteResult, WriteStatus

logger = logging.getLogger(__name__)


class NewsWriteService:

    def __init__(
        self,
        idempotency: IdempotencyStore,
        queue: WriteQueue,
        dead_letter: DeadLetterStore,
        config: MCPConfig,
        mongo_client=None,   # Sprint 1: inject edilebilir, test için None
    ) -> None:
        self._idempotency = idempotency
        self._queue = queue
        self._dead_letter = dead_letter
        self._cfg = config
        self._mongo = mongo_client

    def write(self, request: NewsWriteRequest) -> WriteResult:
        idem_key = request.idempotency_key()

        if self._idempotency.is_duplicate(idem_key):
            existing_id = self._idempotency.get_existing_id(idem_key)
            logger.info(
                "mcp.write.idempotency_hit",
                extra={"idem_key": idem_key[:16], "existing_id": existing_id},
            )
            return WriteResult(
                status=WriteStatus.DUPLICATE_MERGED,
                news_id=existing_id,
                was_duplicate=True,
                idempotency_key=idem_key,
                reason="idempotency_cache_hit",
            )

        error_message: str | None = None

        try:
            return self._mongo_write(request, idem_key)
        except Exception as exc:
            error_message = str(exc)
            logger.warning(
                "mcp.write.mongo_error",
                extra={"error": type(exc).__name__, **request.safe_log_repr()},
            )

        if self._cfg.fail_closed:
            return self._handle_failure(request, idem_key, error_message or "unknown_error")

        logger.error(
            "mcp.write.fail_open_mode",
            extra={"warning": "fail_closed=False - production'da kullanma"},
        )
        return WriteResult(
            status=WriteStatus.DEAD_LETTERED,
            news_id=None,
            was_duplicate=False,
            idempotency_key=idem_key,
            reason="fail_open_no_fallback",
        )

    def _mongo_write(
        self, request: NewsWriteRequest, idem_key: str
    ) -> WriteResult:
        if self._mongo is None:
            fake_id = f"mock_{idem_key[:12]}"
            self._idempotency.mark_processed(idem_key, fake_id)
            logger.info(
                "mcp.write.mock_insert",
                extra={"fake_id": fake_id, **request.safe_log_repr()},
            )
            return WriteResult(
                status=WriteStatus.INSERTED,
                news_id=fake_id,
                was_duplicate=False,
                idempotency_key=idem_key,
            )

        collection = self._mongo[self._cfg.mongo_db]["haberler"]

        doc = {
            "baslik": request.title,
            "url": request.url,
            "kaynak_site": request.source,
            "kaynak_listesi": [request.source],
            "icerik": request.content,
            "ozet": request.summary,
            "gorsel_url": request.image_url,
            "yayin_tarihi": request.published_at,
            "idempotency_key": idem_key,
        }

        result = collection.update_one(
            {"url": request.url},
            {
                "$setOnInsert": doc,
                "$addToSet": {"kaynak_listesi": request.source},
            },
            upsert=True,
        )

        saved = collection.find_one({"url": request.url})
        news_id = str(saved["_id"])

        self._idempotency.mark_processed(idem_key, news_id)

        if result.upserted_id is not None:
            return WriteResult(
                status=WriteStatus.INSERTED,
                news_id=news_id,
                was_duplicate=False,
                idempotency_key=idem_key,
            )

        return WriteResult(
            status=WriteStatus.DUPLICATE_MERGED,
            news_id=news_id,
            was_duplicate=True,
            idempotency_key=idem_key,
        )
    def _handle_failure(
        self, request: NewsWriteRequest, idem_key: str, error: str
    ) -> WriteResult:
        """Queue → dead-letter failure cascade."""
        queued = self._queue.enqueue(request)

        if queued:
            return WriteResult(
                status=WriteStatus.QUEUED,
                news_id=None,
                was_duplicate=False,
                idempotency_key=idem_key,
                reason=f"mongo_down_queued: {error[:60]}",
            )

        # Queue da dolu → dead-letter
        self._dead_letter.add(request, error, attempt_count=0)
        return WriteResult(
            status=WriteStatus.DEAD_LETTERED,
            news_id=None,
            was_duplicate=False,
            idempotency_key=idem_key,
            reason=f"queue_full_dead_lettered: {error[:60]}",
        )