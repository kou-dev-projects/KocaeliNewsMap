from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from app.domain.enums import NewsCategory, normalize_news_category
from app.pipelines import SourceRecordMaterializer
from app.services.embedding import EmbeddingService
from app.services.embedding.schemas import EmbeddingInput, TextEmbedding
from app.services.dataset_generation import resolve_write_generation
from app.services.ner.districts import normalize_for_compare
from app.scrapers.base.date_utils import parse_published_at_raw
from app.utils.content_hash import compute_content_hash, compute_duplicate_hash

from .config import MCPConfig
from .dead_letter import DeadLetterStore
from .idempotency import IdempotencyStore
from .queue import WriteQueue
from .schemas import NewsWriteRequest, WriteResult, WriteStatus

logger = logging.getLogger(__name__)
_GEOCODE_STATUS_RANK = {
    "resolved": 4,
    "approximate": 3,
    "pending": 2,
    "failed": 1,
    "not_needed": 0,
}

_CATEGORY_PRIORITY = {
    NewsCategory.TRAFIK_KAZASI.value: 1,
    NewsCategory.YANGIN.value: 2,
    NewsCategory.HIRSIZLIK.value: 3,
    NewsCategory.ELEKTRIK_KESINTISI.value: 4,
    NewsCategory.KULTUREL_ETKINLIK.value: 5,
    NewsCategory.UNKNOWN.value: 99,
}

_LOCATION_PRECISION_HINTS = (
    "mahallesi",
    "mahalle",
    "sokak",
    "cadde",
    "caddesi",
    "bulvar",
    "blv",
    "meydani",
    "kavsagi",
    "otoyolu",
)


def _merge_unique_sources(*source_groups: list[str] | None) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    for group in source_groups:
        for value in group or []:
            source = str(value or "").strip()
            if not source:
                continue
            source_key = source.casefold()
            if source_key in seen:
                continue
            seen.add(source_key)
            merged.append(source)

    return merged


def _geocode_rank(status: str | None) -> int:
    return _GEOCODE_STATUS_RANK.get(str(status or "").strip(), -1)


def _category_priority(category_value: str | None) -> int:
    normalized = normalize_news_category(category_value)
    if normalized is None:
        return 99
    return _CATEGORY_PRIORITY.get(normalized.value, 99)


def _is_unknown_category(category_value: str | None) -> bool:
    normalized = normalize_news_category(category_value)
    if normalized is None:
        return True
    return normalized is NewsCategory.UNKNOWN


def _location_specificity(value: str | None) -> int:
    if not isinstance(value, str):
        return -1

    text = value.strip()
    if not text:
        return -1

    normalized = normalize_for_compare(text)
    if not normalized:
        return -1

    token_count = len(normalized.split())
    score = min(token_count, 8)

    if any(hint in normalized for hint in _LOCATION_PRECISION_HINTS):
        score += 10
    if "," in text:
        score += 1

    return score


def _has_valid_geocode_point(value: object) -> bool:
    if not isinstance(value, dict):
        return False

    coordinates = value.get("coordinates")
    if value.get("type") != "Point":
        return False
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) != 2:
        return False
    return all(isinstance(item, (int, float)) for item in coordinates)


def _should_promote_geocode(canonical_doc: dict, incoming_doc: dict) -> bool:
    incoming_rank = _geocode_rank(incoming_doc.get("geocode_status"))
    canonical_rank = _geocode_rank(canonical_doc.get("geocode_status"))

    if incoming_rank > canonical_rank:
        return True
    if incoming_rank < canonical_rank:
        return False
    if incoming_rank < 0:
        return False

    if _has_valid_geocode_point(incoming_doc.get("geocode_point")) and not _has_valid_geocode_point(
        canonical_doc.get("geocode_point")
    ):
        return True

    incoming_provider = str(incoming_doc.get("geocode_provider") or "").strip().casefold()
    canonical_provider = str(canonical_doc.get("geocode_provider") or "").strip().casefold()
    if (
        canonical_provider == "district_fallback"
        and incoming_provider
        and incoming_provider != "district_fallback"
    ):
        return True

    return _location_specificity(incoming_doc.get("location_text_extracted")) > _location_specificity(
        canonical_doc.get("location_text_extracted")
    )


def merge_duplicate_source_record_docs(
    canonical_doc: dict,
    incoming_doc: dict,
) -> dict[str, object]:
    update: dict[str, object] = {
        "kaynak_listesi": _merge_unique_sources(
            canonical_doc.get("kaynak_listesi"),
            incoming_doc.get("kaynak_listesi"),
        ),
        "updated_at": incoming_doc.get("updated_at"),
    }

    canonical_category = canonical_doc.get("category_predicted")
    incoming_category = incoming_doc.get("category_predicted")
    canonical_confidence = float(canonical_doc.get("category_confidence") or 0.0)
    incoming_confidence = float(incoming_doc.get("category_confidence") or 0.0)

    canonical_unknown = _is_unknown_category(canonical_category)
    incoming_unknown = _is_unknown_category(incoming_category)

    if not incoming_unknown:
        should_replace_category = False

        if canonical_unknown:
            should_replace_category = True
        elif incoming_category != canonical_category:
            confidence_delta = incoming_confidence - canonical_confidence
            if confidence_delta > 1e-9:
                should_replace_category = True
            elif (
                abs(confidence_delta) <= 1e-9
                and _category_priority(incoming_category) < _category_priority(canonical_category)
            ):
                should_replace_category = True

        if should_replace_category:
            update["category_predicted"] = incoming_category
            update["category_confidence"] = incoming_doc.get("category_confidence")
            update["category_model_version"] = incoming_doc.get("category_model_version")

    if not canonical_doc.get("district_predicted") and incoming_doc.get("district_predicted"):
        update["district_predicted"] = incoming_doc.get("district_predicted")
        update["district_confidence"] = incoming_doc.get("district_confidence")

    if _location_specificity(incoming_doc.get("location_text_extracted")) > _location_specificity(
        canonical_doc.get("location_text_extracted")
    ):
        update["location_text_extracted"] = incoming_doc.get("location_text_extracted")

    if not canonical_doc.get("summary") and incoming_doc.get("summary"):
        update["summary"] = incoming_doc.get("summary")

    canonical_body = str(canonical_doc.get("body") or "")
    incoming_body = str(incoming_doc.get("body") or "")
    if len(incoming_body) > len(canonical_body):
        update["body"] = incoming_doc.get("body")
    if len(str(incoming_doc.get("summary") or "")) > len(str(canonical_doc.get("summary") or "")):
        update["summary"] = incoming_doc.get("summary")

    if _should_promote_geocode(canonical_doc, incoming_doc):
        for field in (
            "geocode_status",
            "geocode_provider",
            "geocode_provider_version",
            "geocode_point",
            "geocode_bbox",
            "location_resolution_method",
            "district_predicted",
            "district_confidence",
            "location_text_extracted",
        ):
            if field in incoming_doc:
                update[field] = incoming_doc.get(field)

    return update


class NewsWriteService:
    def __init__(
        self,
        idempotency: IdempotencyStore,
        queue: WriteQueue,
        dead_letter: DeadLetterStore,
        config: MCPConfig,
        mongo_client=None,
        materializer: SourceRecordMaterializer | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._idempotency = idempotency
        self._queue = queue
        self._dead_letter = dead_letter
        self._cfg = config
        self._mongo = mongo_client
        self._materializer = materializer or SourceRecordMaterializer()
        self._embedding_service = embedding_service

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
        dataset_generation = resolve_write_generation(
            database,
            requested_generation=request.dataset_generation,
        )

        raw_documents = database["raw_documents"]
        raw_document = self._build_raw_document(
            request=request,
            source_doc=source_doc,
            crawl_session_id=crawl_session_id,
            dataset_generation=dataset_generation,
        )
        raw_document_update = {
            key: value for key, value in raw_document.items() if key != "created_at"
        }
        raw_filter = {
            "source_id": source_doc["_id"],
            "canonical_url": request.url,
        }
        if dataset_generation is not None:
            raw_filter["dataset_generation"] = dataset_generation
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
        if dataset_generation is not None:
            source_record["dataset_generation"] = dataset_generation
        source_record["dedupe_hash"] = source_record.get("dedupe_hash") or self._duplicate_hash(
            title=str(source_record.get("title") or request.title),
            body=str(source_record.get("body") or request.content or ""),
            summary=str(source_record.get("summary") or request.summary or ""),
        )
        source_records = database["source_records"]
        source_record_filter = {"raw_document_id": saved_raw_document["_id"]}
        existing_source_record = source_records.find_one(source_record_filter)
        duplicate_target = self._find_duplicate_target(
            source_records=source_records,
            source_record=source_record,
            raw_document_id=saved_raw_document["_id"],
            dataset_generation=dataset_generation,
        )
        source_record_update = {
            key: value for key, value in source_record.items() if key != "created_at"
        }
        is_cross_source_duplicate = (
            duplicate_target is not None
            and (
                existing_source_record is None
                or str(duplicate_target.get("_id")) != str(existing_source_record.get("_id"))
            )
        )

        if is_cross_source_duplicate:
            canonical_update = merge_duplicate_source_record_docs(
                duplicate_target,
                source_record,
            )
            source_records.update_one(
                {"_id": duplicate_target["_id"]},
                {"$set": canonical_update},
                upsert=False,
            )
            duplicate_record_update = {
                **source_record_update,
                "record_status": "merged_duplicate",
                "duplicate_of_record_id": duplicate_target["_id"],
                "kaynak_listesi": source_record.get("kaynak_listesi") or [request.source],
            }
            source_records.update_one(
                source_record_filter,
                {
                    "$set": duplicate_record_update,
                    "$setOnInsert": {
                        "created_at": source_record["updated_at"],
                    },
                },
                upsert=True,
            )

            news_id = str(duplicate_target["_id"])
            self._idempotency.mark_processed(idem_key, news_id)
            return WriteResult(
                status=WriteStatus.DUPLICATE_MERGED,
                news_id=news_id,
                was_duplicate=True,
                idempotency_key=idem_key,
                reason="cross_source_duplicate_merged",
            )

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

    def _find_duplicate_target(
        self,
        *,
        source_records,
        source_record: dict,
        raw_document_id: ObjectId,
        dataset_generation: str | None,
    ) -> dict | None:
        hash_duplicate_target = self._find_hash_duplicate_target(
            source_records=source_records,
            source_record=source_record,
            raw_document_id=raw_document_id,
            dataset_generation=dataset_generation,
        )
        if hash_duplicate_target is not None:
            source_record.update(
                {
                    "duplicate_status": "duplicate",
                    "duplicate_source_record_id": hash_duplicate_target["_id"],
                    "duplicate_text_similarity": 1.0,
                    "duplicate_final_score": 1.0,
                    "duplicate_threshold": self._duplicate_threshold(),
                    "duplicate_reason": "dedupe_hash_match",
                }
            )
            return hash_duplicate_target

        semantic_duplicate_target = self._find_semantic_duplicate_target(
            source_records=source_records,
            source_record=source_record,
            raw_document_id=raw_document_id,
            dataset_generation=dataset_generation,
        )
        if semantic_duplicate_target is not None:
            return semantic_duplicate_target

        return None

    def _find_hash_duplicate_target(
        self,
        *,
        source_records,
        source_record: dict,
        raw_document_id: ObjectId,
        dataset_generation: str | None,
    ) -> dict | None:
        dedupe_hash = str(source_record.get("dedupe_hash") or "").strip()
        if not dedupe_hash:
            return None

        query: dict[str, object] = {
            "dedupe_hash": dedupe_hash,
            "record_status": {"$ne": "merged_duplicate"},
            "raw_document_id": {"$ne": raw_document_id},
        }
        if dataset_generation is not None:
            query["dataset_generation"] = dataset_generation

        return source_records.find_one(query)

    def _find_semantic_duplicate_target(
        self,
        *,
        source_records,
        source_record: dict,
        raw_document_id: ObjectId,
        dataset_generation: str | None,
    ) -> dict | None:
        if self._embedding_service is None:
            return None

        incoming_embedding = self._ensure_text_embedding(source_record)
        if incoming_embedding is None:
            source_record["duplicate_status"] = "skipped"
            source_record["duplicate_reason"] = "semantic_embedding_unavailable"
            return None

        source_record["duplicate_status"] = "unique"
        source_record["duplicate_threshold"] = self._duplicate_threshold()

        candidate_query: dict[str, object] = {
            "record_status": "active",
            "raw_document_id": {"$ne": raw_document_id},
        }
        if dataset_generation is not None:
            candidate_query["dataset_generation"] = dataset_generation

        candidates: list[dict] = []
        candidate_docs_by_id: dict[str, dict] = {}

        for index, candidate_doc in enumerate(source_records.find(candidate_query)):
            if index >= 250:
                break

            candidate_embedding = self._ensure_text_embedding(candidate_doc)
            if candidate_embedding is None:
                continue

            candidate_id = str(candidate_doc.get("_id"))
            candidate_docs_by_id[candidate_id] = candidate_doc
            candidates.append(
                {
                    "id": candidate_id,
                    "text_vector": candidate_embedding.vector,
                    "image_vector": None,
                    "kaynak_listesi": candidate_doc.get("kaynak_listesi", []),
                }
            )

        if not candidates:
            source_record["duplicate_reason"] = "semantic_no_candidates"
            return None

        try:
            try:
                duplicate_score = self._embedding_service.decide_duplicate(
                    incoming_text=incoming_embedding,
                    candidates=candidates,
                    new_source=str((source_record.get("kaynak_listesi") or [""])[0]),
                )
            except TypeError:
                duplicate_score = self._embedding_service.decide_duplicate(
                    incoming_text=incoming_embedding,
                    incoming_image=None,
                    candidates=candidates,
                    new_source=str((source_record.get("kaynak_listesi") or [""])[0]),
                )
        except Exception as exc:
            logger.warning(
                "mcp.write.semantic_duplicate_failed",
                extra={"error": f"{type(exc).__name__}: {exc}"},
            )
            source_record["duplicate_status"] = "error"
            source_record["duplicate_reason"] = "semantic_duplicate_failed"
            return None

        source_record.update(
            {
                "duplicate_text_similarity": duplicate_score.text_similarity,
                "duplicate_final_score": duplicate_score.final_score,
                "duplicate_threshold": self._duplicate_threshold(),
                "duplicate_reason": (
                    "semantic_text_similarity_match"
                    if duplicate_score.is_duplicate
                    else "semantic_below_threshold"
                ),
            }
        )

        if not duplicate_score.is_duplicate or duplicate_score.matched_news_id is None:
            return None

        matched_doc = candidate_docs_by_id.get(duplicate_score.matched_news_id)
        if matched_doc is None:
            return None

        source_record["duplicate_status"] = "duplicate"
        source_record["duplicate_source_record_id"] = matched_doc["_id"]
        return matched_doc

    def _ensure_text_embedding(self, source_record: dict) -> TextEmbedding | None:
        existing_vector = source_record.get("text_embedding")
        if isinstance(existing_vector, list) and existing_vector:
            return TextEmbedding(
                vector=[float(value) for value in existing_vector],
                dimension=int(source_record.get("text_embedding_dim") or len(existing_vector)),
                provider=str(source_record.get("text_embedding_model") or "stored-text-embedding"),
            )

        if self._embedding_service is None:
            return None

        try:
            embedding_result = self._embedding_service.embed(
                EmbeddingInput(
                    title=str(source_record.get("title") or ""),
                    summary=str(source_record.get("summary") or "") or None,
                    content=str(source_record.get("body") or "") or None,
                    source=self._embedding_source_label(source_record),
                )
            )
            if isinstance(embedding_result, tuple):
                text_embedding = embedding_result[0]
            else:
                text_embedding = embedding_result
        except Exception as exc:
            logger.warning(
                "mcp.write.text_embedding_failed",
                extra={"error": f"{type(exc).__name__}: {exc}"},
            )
            return None

        source_record["text_embedding"] = text_embedding.vector
        source_record["text_embedding_model"] = text_embedding.provider
        source_record["text_embedding_dim"] = text_embedding.dimension
        return text_embedding

    def _embedding_source_label(self, source_record: dict) -> str:
        kaynak_listesi = source_record.get("kaynak_listesi") or []
        if kaynak_listesi:
            return str(kaynak_listesi[0])
        source_name = str(source_record.get("source_name_snapshot") or "").strip()
        if source_name:
            return source_name
        return "unknown"

    def _duplicate_threshold(self) -> float | None:
        if self._embedding_service is None:
            return None
        return float(getattr(getattr(self._embedding_service, "_cfg", None), "duplicate_threshold", 0.90))

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
        dataset_generation: str | None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        published_at = parse_published_at_raw(request.published_at)
        scraped_at = parse_published_at_raw(request.scraped_at) or now
        text_raw = request.content or request.summary or request.title
        content_hash = self._content_hash(request.title, text_raw)

        raw_document = {
            "source_id": source_doc["_id"],
            "crawl_session_id": crawl_session_id,
            "canonical_url": request.url,
            "resolved_url": request.resolved_url or request.url,
            "domain": request.source,
            "title_raw": request.title,
            "text_raw": text_raw,
            "content_raw": request.content or "",
            "published_at_raw": published_at,
            "language": "tr",
            "content_hash": content_hash,
            "fetch_status": "success",
            "parser_version": request.parser_version,
            "schema_version": "1.0",
            "scraped_at": scraped_at,
            "created_at": now,
            "updated_at": now,
        }
        if dataset_generation is not None:
            raw_document["dataset_generation"] = dataset_generation
        return raw_document

    def _content_hash(self, title: str, text_raw: str) -> str:
        return compute_content_hash(title=title, body=text_raw)

    def _duplicate_hash(self, *, title: str, body: str, summary: str) -> str:
        return compute_duplicate_hash(title=title, body=body, summary=summary)

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
