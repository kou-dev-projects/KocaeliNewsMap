from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from bson import ObjectId
from bson.errors import InvalidId

from app.pipelines import SourceRecordMaterializer
from app.scrapers.base.date_utils import parse_published_at_raw
from app.utils.content_hash import compute_content_hash

from .config import MCPConfig
from .dead_letter import DeadLetterStore
from .idempotency import IdempotencyStore
from .queue import WriteQueue
from .schemas import NewsWriteRequest, WriteResult, WriteStatus

logger = logging.getLogger(__name__)


class NewsWriteService:
    def __init__(
        self,
        idempotency: IdempotencyStore,
        queue: WriteQueue,
        dead_letter: DeadLetterStore,
        config: MCPConfig,
        mongo_client=None,
        materializer: SourceRecordMaterializer | None = None,
    ) -> None:
        self._idempotency = idempotency
        self._queue = queue
        self._dead_letter = dead_letter
        self._cfg = config
        self._mongo = mongo_client
        self._materializer = materializer or SourceRecordMaterializer()

    def write(self, request: NewsWriteRequest) -> WriteResult:
        idem_key = request.idempotency_key()

        if self._idempotency.is_duplicate(idem_key):
            existing_id = self._idempotency.get_existing_id(idem_key)
            logger.info(
                "mcp.write.idempotency_refresh",
                extra={
                    "idem_key": idem_key[:16],
                    "existing_id": existing_id,
                    "reason": "recompute_materialized_record",
                },
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
            extra={"warning": "fail_closed=False - do not use in production"},
        )
        return WriteResult(
            status=WriteStatus.DEAD_LETTERED,
            news_id=None,
            was_duplicate=False,
            idempotency_key=idem_key,
            reason="fail_open_no_fallback",
        )

    def process_queue_batch(self, *, batch_size: int = 20) -> dict[str, int]:
        items = self._queue.dequeue_batch(size=max(batch_size, 1))
        summary = {
            "dequeued": len(items),
            "processed": 0,
            "requeued": 0,
            "dead_lettered": 0,
        }

        for item in items:
            request = item.request
            idem_key = request.idempotency_key()

            if self._idempotency.is_duplicate(idem_key):
                logger.info(
                    "mcp.write.queue_idempotency_refresh",
                    extra={"idem_key": idem_key[:16]},
                )

            try:
                self._mongo_write(request, idem_key)
                summary["processed"] += 1
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                if self._queue.requeue(item, error):
                    summary["requeued"] += 1
                    continue

                self._dead_letter.add(
                    request,
                    error,
                    attempt_count=item.attempt_count,
                )
                summary["dead_lettered"] += 1

        if summary["dequeued"] > 0:
            logger.info("mcp.write.queue_batch_processed", extra=summary)

        return summary

    def _mongo_write(self, request: NewsWriteRequest, idem_key: str) -> WriteResult:
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

        database = self._mongo[self._cfg.mongo_db]
        source_doc = self._get_source_document(database, request.source)
        crawl_session_id = self._resolve_crawl_session_id(database, request, source_doc)

        raw_documents = database["raw_documents"]
        raw_document = self._build_raw_document(
            request=request,
            source_doc=source_doc,
            crawl_session_id=crawl_session_id,
        )
        raw_document_update = {
            key: value for key, value in raw_document.items() if key != "created_at"
        }
        raw_filter = {
            "source_id": source_doc["_id"],
            "canonical_url": request.url,
        }
        raw_result = raw_documents.update_one(
            raw_filter,
            {
                "$set": raw_document_update,
                "$setOnInsert": {
                    "created_at": raw_document["created_at"],
                },
            },
            upsert=True,
        )

        saved_raw_document = raw_documents.find_one(raw_filter)
        if saved_raw_document is None:
            raise RuntimeError("raw_document_write_failed")

        source_record = self._materializer.materialize(
            raw_document=saved_raw_document,
            source_document=source_doc,
        )
        source_record_update = {
            key: value for key, value in source_record.items() if key != "created_at"
        }
        source_records = database["source_records"]
        source_record_filter = {"raw_document_id": saved_raw_document["_id"]}
        source_record_result = source_records.update_one(
            source_record_filter,
            {
                "$set": source_record_update,
                "$setOnInsert": {
                    "created_at": source_record["updated_at"],
                },
            },
            upsert=True,
        )

        saved_source_record = source_records.find_one(source_record_filter)
        if saved_source_record is None:
            raise RuntimeError("source_record_write_failed")

        news_id = str(saved_source_record["_id"])
        self._idempotency.mark_processed(idem_key, news_id)

        if raw_result.upserted_id is not None or source_record_result.upserted_id is not None:
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

    def _get_source_document(self, database, domain: str) -> dict:
        source_doc = database["sources"].find_one({"domain": domain})
        if source_doc is None:
            raise ValueError(f"unknown_source_domain: {domain}")
        return source_doc

    def _resolve_crawl_session_id(self, database, request: NewsWriteRequest, source_doc: dict) -> ObjectId:
        if request.crawl_session_id:
            try:
                return ObjectId(request.crawl_session_id)
            except InvalidId as exc:
                raise ValueError("invalid_crawl_session_id") from exc

        now = datetime.now(timezone.utc)
        crawl_session = {
            "source_id": source_doc["_id"],
            "trigger_type": "manual",
            "scope": "single_source",
            "lookback_days": 1,
            "started_at": now,
            "ended_at": now,
            "status": "success",
            "fetched_count": 1,
            "parsed_count": 1,
            "failed_count": 0,
            "error_summary": [],
            "worker_version": "mcp_write_service",
            "trace_id": request.idempotency_key()[:16],
            "created_at": now,
            "updated_at": now,
        }
        result = database["crawl_sessions"].insert_one(crawl_session)
        return result.inserted_id

    def _build_raw_document(
        self,
        *,
        request: NewsWriteRequest,
        source_doc: dict,
        crawl_session_id: ObjectId,
    ) -> dict:
        now = datetime.now(timezone.utc)
        published_at = parse_published_at_raw(request.published_at)
        scraped_at = parse_published_at_raw(request.scraped_at) or now
        text_raw = request.content or request.summary or request.title
        content_hash = self._content_hash(request.title, text_raw)
        image_urls_raw = self._build_image_urls_raw(
            image_url=request.image_url,
            source_base_url=source_doc.get("base_url", ""),
            resolved_url=request.resolved_url or request.url,
        )

        return {
            "source_id": source_doc["_id"],
            "crawl_session_id": crawl_session_id,
            "canonical_url": request.url,
            "resolved_url": request.resolved_url or request.url,
            "domain": request.source,
            "title_raw": request.title,
            "text_raw": text_raw,
            "content_raw": request.content or "",
            "published_at_raw": published_at,
            "image_urls_raw": image_urls_raw,
            "language": "tr",
            "content_hash": content_hash,
            "fetch_status": "success",
            "parser_version": request.parser_version,
            "schema_version": "1.0",
            "scraped_at": scraped_at,
            "created_at": now,
            "updated_at": now,
        }

    def _content_hash(self, title: str, text_raw: str) -> str:
        return compute_content_hash(title=title, body=text_raw)

    def _build_image_urls_raw(
        self,
        *,
        image_url: str | None,
        source_base_url: str,
        resolved_url: str,
    ) -> list[str]:
        if not image_url:
            return []

        normalized = image_url.strip()
        if not normalized:
            return []

        base_url = resolved_url or source_base_url
        normalized = urljoin(base_url, normalized)

        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            logger.info(
                "mcp.write.invalid_image_url_skipped",
                extra={"image_url": image_url},
            )
            return []

        return [normalized]

    def _handle_failure(
        self, request: NewsWriteRequest, idem_key: str, error: str
    ) -> WriteResult:
        queued = self._queue.enqueue(request)

        if queued:
            return WriteResult(
                status=WriteStatus.QUEUED,
                news_id=None,
                was_duplicate=False,
                idempotency_key=idem_key,
                reason=f"mongo_down_queued: {error[:60]}",
            )

        self._dead_letter.add(request, error, attempt_count=0)
        return WriteResult(
            status=WriteStatus.DEAD_LETTERED,
            news_id=None,
            was_duplicate=False,
            idempotency_key=idem_key,
            reason=f"queue_full_dead_lettered: {error[:60]}",
        )
