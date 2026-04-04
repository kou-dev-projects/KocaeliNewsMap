from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import os
import sys
from socket import gethostname
from typing import Any, Callable
from uuid import uuid4

from app.scrapers.cagdas_kocaeli.detail import CagdasKocaeliDetailScraper
from app.scrapers.cagdas_kocaeli.listing import CagdasKocaeliListingScraper
from app.scrapers.cagdas_kocaeli.parser import CagdasKocaeliParser
from app.scrapers.base.playwright_client import PlaywrightClient
from app.scrapers.bizim_yaka.detail import BizimYakaDetailScraper
from app.scrapers.bizim_yaka.listing import BizimYakaListingScraper
from app.scrapers.base.date_utils import parse_published_at_raw
from app.scrapers.ozgur_kocaeli.detail import OzgurKocaeliDetailScraper
from app.scrapers.ozgur_kocaeli.listing import OzgurKocaeliListingScraper
from app.scrapers.ozgur_kocaeli.parser import OzgurKocaeliParser
from app.scrapers.ses_kocaeli.detail import SesKocaeliDetailScraper
from app.scrapers.ses_kocaeli.listing import SesKocaeliListingScraper
from app.scrapers.yeni_kocaeli.detail import YeniKocaeliDetailScraper
from app.scrapers.yeni_kocaeli.listing import YeniKocaeliListingScraper
from app.scrapers.yeni_kocaeli.parser import YeniKocaeliParser
from app.services.mcp.lease import SourceLease
from app.services.mcp.schemas import NewsWriteRequest
from app.services.mcp.server import create_write_services
from app.services.mcp.write_service import NewsWriteService
from app.settings import settings

from .config import SchedulerConfig, load_scheduler_config
from .sessions import CrawlSessionStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StaticSourceDefinition:
    listing_scraper_factory: Callable[[], Any]
    detail_scraper_factory: Callable[[], Any]
    parser_factory: Callable[[], Any]


@dataclass(frozen=True)
class DynamicSourceDefinition:
    listing_scraper_factory: Callable[[PlaywrightClient, str], Any]
    detail_scraper_factory: Callable[[PlaywrightClient], Any]
    max_urls_override: int | None = None
    per_url_delay_seconds: float = 0.0


STATIC_SOURCE_REGISTRY: dict[str, StaticSourceDefinition] = {
    "cagdaskocaeli.com.tr": StaticSourceDefinition(
        listing_scraper_factory=CagdasKocaeliListingScraper,
        detail_scraper_factory=CagdasKocaeliDetailScraper,
        parser_factory=CagdasKocaeliParser,
    ),
    "ozgurkocaeli.com.tr": StaticSourceDefinition(
        listing_scraper_factory=OzgurKocaeliListingScraper,
        detail_scraper_factory=OzgurKocaeliDetailScraper,
        parser_factory=OzgurKocaeliParser,
    ),
    "yenikocaeli.com": StaticSourceDefinition(
        listing_scraper_factory=YeniKocaeliListingScraper,
        detail_scraper_factory=YeniKocaeliDetailScraper,
        parser_factory=YeniKocaeliParser,
    ),
}


DYNAMIC_SOURCE_REGISTRY: dict[str, DynamicSourceDefinition] = {
    "seskocaeli.com": DynamicSourceDefinition(
        listing_scraper_factory=lambda client, base_url: SesKocaeliListingScraper(
            client=client,
            listing_url=base_url,
        ),
        detail_scraper_factory=lambda client: SesKocaeliDetailScraper(client=client),
        max_urls_override=1,
        per_url_delay_seconds=8.0,
    ),
    "bizimyaka.com": DynamicSourceDefinition(
        listing_scraper_factory=lambda client, base_url: BizimYakaListingScraper(
            client=client,
            listing_url=base_url,
        ),
        detail_scraper_factory=lambda client: BizimYakaDetailScraper(client=client),
    ),
}


class ScrapeOrchestrator:
    def __init__(
        self,
        *,
        config: SchedulerConfig | None = None,
        database=None,
        write_service: NewsWriteService | None = None,
        lease: SourceLease | None = None,
        session_store: CrawlSessionStore | None = None,
    ) -> None:
        self._config = config or load_scheduler_config()
        if database is None:
            from app.db.database import db as default_db

            self._db = default_db
        else:
            self._db = database

        if write_service is not None and lease is not None:
            self._write_service = write_service
            self._lease = lease
        else:
            self._write_service, self._lease = create_write_services()

        self._sessions = session_store or CrawlSessionStore(self._db)
        worker_label = settings.worker_id or "worker"
        self._worker_id = f"{worker_label}:{gethostname()}:{os.getpid()}"

    @property
    def database(self):
        return self._db

    def drain_pending_writes(self, *, batch_size: int = 50) -> dict[str, Any]:
        try:
            result = self._write_service.process_queue_batch(batch_size=batch_size)
            if result.get("dequeued", 0) > 0:
                logger.info("scheduler.queue_drain.finished", extra=result)
            return result
        except Exception:
            logger.exception("scheduler.queue_drain.failed")
            return {
                "dequeued": 0,
                "processed": 0,
                "requeued": 0,
                "dead_lettered": 0,
                "status": "failed",
            }

    def _crawl_active_sources(
        self,
        *,
        trigger_type: str = "scheduled",
        dataset_generation: str | None = None,
    ) -> dict[str, Any]:
        active_sources = self._list_active_sources()

        summary = {
            "active_sources": len(active_sources),
            "processed_sources": 0,
            "skipped_sources": 0,
            "skipped_session_reasons": [],
            "sessions": [],
        }
        if dataset_generation:
            summary["dataset_generation"] = dataset_generation

        for source_document in active_sources:
            domain = source_document["domain"]
            try:
                session_result = self._crawl_single_source(
                    source_document=source_document,
                    trigger_type=trigger_type,
                    dataset_generation=dataset_generation,
                )
            except Exception as exc:
                logger.exception(
                    "scheduler.source.unhandled_error",
                    extra={
                        "domain": domain,
                        "trigger_type": trigger_type,
                        "error_type": type(exc).__name__,
                    },
                )
                session_result = {
                    "domain": domain,
                    "status": "failed",
                    "reason": "unhandled_source_exception",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)[:500],
                }
            if session_result.get("status") == "skipped":
                summary["skipped_sources"] += 1
                summary["skipped_session_reasons"].append(
                    str(session_result.get("reason") or "unknown")
                )
                continue

            summary["processed_sources"] += 1
            summary["sessions"].append(session_result)

        return summary

    def crawl_active_sources(
        self,
        *,
        trigger_type: str = "scheduled",
        dataset_generation: str | None = None,
    ) -> dict[str, Any]:
        return self._crawl_active_sources(
            trigger_type=trigger_type,
            dataset_generation=dataset_generation,
        )

    def crawl_source(self, domain: str, *, trigger_type: str = "manual") -> dict[str, Any]:
        source_document = self._db["sources"].find_one(
            {"domain": domain, "active": True},
            {"domain": 1, "base_url": 1, "scraper_type": 1, "display_name": 1},
        )
        if source_document is None:
            raise ValueError(f"active_source_not_found: {domain}")
        return self._crawl_single_source(
            source_document=source_document,
            trigger_type=trigger_type,
            dataset_generation=None,
        )

    def _crawl_single_source(
        self,
        *,
        source_document: dict[str, Any],
        trigger_type: str,
        dataset_generation: str | None,
    ) -> dict[str, Any]:
        domain = source_document["domain"]

        if domain.lower() in self._config.skipped_domains:
            logger.info(
                "scheduler.source.skipped_by_config",
                extra={"domain": domain},
            )
            return {
                "domain": domain,
                "status": "skipped",
                "reason": "skipped_by_config",
            }

        if domain in STATIC_SOURCE_REGISTRY:
            return self._crawl_single_source_static(
                source_document=source_document,
                trigger_type=trigger_type,
                dataset_generation=dataset_generation,
            )
        if domain in DYNAMIC_SOURCE_REGISTRY:
            return self._crawl_single_source_dynamic(
                source_document=source_document,
                trigger_type=trigger_type,
                dataset_generation=dataset_generation,
            )

        logger.info(
            "scheduler.source.unsupported",
            extra={"domain": domain, "scraper_type": source_document.get("scraper_type")},
        )
        return {
            "domain": domain,
            "status": "skipped",
            "reason": "unsupported_source",
        }

    def _write_news_record(
        self,
        record: dict[str, Any],
        crawl_session_id: str,
        parser_version: str,
        dataset_generation: str | None,
    ) -> dict[str, Any]:
        request = NewsWriteRequest(
            title=record["title"],
            url=record["url"],
            source=record["source_domain"],
            content=record.get("content_text", ""),
            summary=record.get("summary", ""),
            image_url=record.get("image_url", ""),
            published_at=record.get("published_at_raw", ""),
            crawl_session_id=crawl_session_id,
            dataset_generation=dataset_generation,
            resolved_url=record["url"],
            scraped_at=record.get("scraped_at", ""),
            parser_version=parser_version,
        )
        result = self._write_service.write(request)
        return {
            "status": result.status.value,
            "news_id": result.news_id,
            "was_duplicate": result.was_duplicate,
            "reason": result.reason,
        }

    def _is_record_within_lookback(self, published_at_raw: Any) -> bool:
        if not isinstance(published_at_raw, str) or not published_at_raw.strip():
            return True

        published_at = parse_published_at_raw(published_at_raw)
        if published_at is None:
            return True

        threshold = datetime.now(timezone.utc) - timedelta(days=self._config.lookback_days)
        return published_at >= threshold

    def _crawl_single_source_static(
        self,
        *,
        source_document: dict[str, Any],
        trigger_type: str,
        dataset_generation: str | None,
    ) -> dict[str, Any]:
        domain = source_document["domain"]
        trace_id = uuid4().hex[:16]

        if not self._lease.acquire(domain, self._worker_id):
            logger.info(
                "scheduler.source.lease_not_acquired",
                extra={"domain": domain, "worker_id": self._worker_id},
            )
            return {
                "domain": domain,
                "status": "skipped",
                "reason": "lease_not_acquired",
            }

        stats = {
            "fetched_count": 0,
            "parsed_count": 0,
            "failed_count": 0,
            "error_summary": [],
        }
        session_id = None
        final_status = "failed"
        listing_scraper = None
        detail_scraper = None
        parser = None

        try:
            session_id = self._sessions.create_for_source(
                source_id=source_document["_id"],
                trigger_type=trigger_type,
                lookback_days=self._config.lookback_days,
                worker_version="scheduler_v1",
                trace_id=trace_id,
                dataset_generation=dataset_generation,
            )

            definition = STATIC_SOURCE_REGISTRY[domain]
            listing_scraper = definition.listing_scraper_factory()
            detail_scraper = definition.detail_scraper_factory()
            parser = definition.parser_factory()

            listing_html = listing_scraper.fetch_listing_html(source_document["base_url"])
            urls = listing_scraper.extract_news_urls(listing_html)[: self._config.max_urls_per_source]

            if not urls:
                self._append_error(
                    stats["error_summary"],
                    code="no_listing_urls",
                    message="No news urls extracted from listing page",
                )

            for target_url in urls:
                try:
                    detail_html = detail_scraper.fetch_detail_html(target_url)
                    stats["fetched_count"] += 1
                    detail_data = detail_scraper.extract_detail_fields(detail_html)
                    record = parser.build_record(target_url, detail_data)

                    if not self._is_record_within_lookback(record.get("published_at_raw")):
                        continue

                    if not record.get("title", "").strip() or not record.get("content_text", "").strip():
                        stats["failed_count"] += 1
                        self._append_error(
                            stats["error_summary"],
                            code="invalid_record",
                            message="Parsed record is missing title or content",
                            sample_url=target_url,
                        )
                        continue

                    write_result = self._write_news_record(
                        record=record,
                        crawl_session_id=str(session_id),
                        parser_version=parser.__class__.__name__,
                        dataset_generation=dataset_generation,
                    )

                    if write_result["status"] in {"inserted", "duplicate_merged"}:
                        stats["parsed_count"] += 1
                        continue

                    stats["failed_count"] += 1
                    self._append_error(
                        stats["error_summary"],
                        code=f"write_{write_result['status']}",
                        message=write_result.get("reason") or "Write pipeline returned non-success status",
                        sample_url=target_url,
                    )
                except Exception as exc:
                    stats["failed_count"] += 1
                    self._append_error(
                        stats["error_summary"],
                        code="source_processing_error",
                        message=f"{type(exc).__name__}: {exc}",
                        error_type=type(exc).__name__,
                        sample_url=target_url,
                    )

        except Exception as exc:
            stats["failed_count"] += 1
            self._append_error(
                stats["error_summary"],
                code="source_bootstrap_error",
                message=f"{type(exc).__name__}: {exc}",
                error_type=type(exc).__name__,
            )
        finally:
            if session_id is not None:
                try:
                    final_status = self._sessions.finalize(
                        session_id=session_id,
                        fetched_count=stats["fetched_count"],
                        parsed_count=stats["parsed_count"],
                        failed_count=stats["failed_count"],
                        error_summary=stats["error_summary"],
                    )
                except Exception:
                    logger.exception(
                        "scheduler.source.session_finalize_failed",
                        extra={"domain": domain, "session_id": str(session_id)},
                    )

            self._close_scraper(listing_scraper)
            self._close_scraper(detail_scraper)
            try:
                self._lease.release(domain, self._worker_id)
            except Exception:
                logger.exception(
                    "scheduler.source.lease_release_failed",
                    extra={"domain": domain, "worker_id": self._worker_id},
                )

        return {
            "domain": domain,
            "status": final_status,
            "session_id": str(session_id) if session_id is not None else None,
            "fetched_count": stats["fetched_count"],
            "parsed_count": stats["parsed_count"],
            "failed_count": stats["failed_count"],
            **self._summarize_error_details(stats["error_summary"]),
        }

    def _crawl_single_source_dynamic(
        self,
        *,
        source_document: dict[str, Any],
        trigger_type: str,
        dataset_generation: str | None,
    ) -> dict[str, Any]:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        return asyncio.run(
            self._crawl_single_source_dynamic_async(
                source_document=source_document,
                trigger_type=trigger_type,
                dataset_generation=dataset_generation,
            )
        )

    async def _crawl_single_source_dynamic_async(
        self,
        *,
        source_document: dict[str, Any],
        trigger_type: str,
        dataset_generation: str | None,
    ) -> dict[str, Any]:
        domain = source_document["domain"]
        trace_id = uuid4().hex[:16]

        if not self._lease.acquire(domain, self._worker_id):
            logger.info(
                "scheduler.source.lease_not_acquired",
                extra={"domain": domain, "worker_id": self._worker_id},
            )
            return {
                "domain": domain,
                "status": "skipped",
                "reason": "lease_not_acquired",
            }

        session_id = None
        stats = {
            "fetched_count": 0,
            "parsed_count": 0,
            "failed_count": 0,
            "error_summary": [],
        }
        definition = DYNAMIC_SOURCE_REGISTRY[domain]
        client = PlaywrightClient(headless=True, timeout_ms=30_000)
        listing_scraper = None
        detail_scraper = None
        final_status = "failed"

        try:
            session_id = self._sessions.create_for_source(
                source_id=source_document["_id"],
                trigger_type=trigger_type,
                lookback_days=self._config.lookback_days,
                worker_version="scheduler_v1",
                trace_id=trace_id,
                dataset_generation=dataset_generation,
            )

            try:
                listing_scraper = definition.listing_scraper_factory(client, source_document["base_url"])
                detail_scraper = definition.detail_scraper_factory(client)

                urls = await listing_scraper.fetch_links()
                max_urls = self._config.max_urls_per_source
                if definition.max_urls_override is not None:
                    max_urls = max(definition.max_urls_override, 1)
                urls = urls[:max_urls]

                per_url_delay = max(definition.per_url_delay_seconds, 0.0)

                if not urls:
                    self._append_error(
                        stats["error_summary"],
                        code="no_listing_urls",
                        message="No news urls extracted from listing page",
                    )

                for target_url in urls:
                    if per_url_delay > 0:
                        await asyncio.sleep(per_url_delay)

                    try:
                        detail_data = await detail_scraper.fetch_detail(target_url)
                        stats["fetched_count"] += 1

                        record = {
                            "source_domain": domain,
                            "source_name": source_document.get("display_name", ""),
                            "source_base_url": source_document.get("base_url", ""),
                            "url": target_url,
                            "title": detail_data.get("title", ""),
                            "summary": detail_data.get("summary", ""),
                            "content_text": detail_data.get("content", ""),
                            "published_at_raw": detail_data.get("published_at_raw", ""),
                            "image_url": detail_data.get("image_url", ""),
                            "scraped_at": datetime.now(timezone.utc).isoformat(),
                        }

                        if not self._is_record_within_lookback(record.get("published_at_raw")):
                            continue

                        if not record.get("title", "").strip() or not record.get("content_text", "").strip():
                            stats["failed_count"] += 1
                            self._append_error(
                                stats["error_summary"],
                                code="invalid_record",
                                message="Parsed record is missing title or content",
                                sample_url=target_url,
                            )
                            continue

                        write_result = self._write_news_record(
                            record=record,
                            crawl_session_id=str(session_id),
                            parser_version=detail_scraper.__class__.__name__,
                            dataset_generation=dataset_generation,
                        )

                        if write_result["status"] in {"inserted", "duplicate_merged"}:
                            stats["parsed_count"] += 1
                            continue

                        stats["failed_count"] += 1
                        self._append_error(
                            stats["error_summary"],
                            code=f"write_{write_result['status']}",
                            message=write_result.get("reason") or "Write pipeline returned non-success status",
                            sample_url=target_url,
                        )
                    except Exception as exc:
                        stats["failed_count"] += 1
                        self._append_error(
                            stats["error_summary"],
                            code="source_processing_error",
                            message=f"{type(exc).__name__}: {exc}",
                            error_type=type(exc).__name__,
                            sample_url=target_url,
                        )
            except Exception as exc:
                stats["failed_count"] += 1
                self._append_error(
                    stats["error_summary"],
                    code="source_bootstrap_error",
                    message=f"{type(exc).__name__}: {exc}",
                    error_type=type(exc).__name__,
                )

            if session_id is not None:
                try:
                    final_status = self._sessions.finalize(
                        session_id=session_id,
                        fetched_count=stats["fetched_count"],
                        parsed_count=stats["parsed_count"],
                        failed_count=stats["failed_count"],
                        error_summary=stats["error_summary"],
                    )
                except Exception:
                    logger.exception(
                        "scheduler.source.session_finalize_failed",
                        extra={"domain": domain, "session_id": str(session_id)},
                    )

            return {
                "domain": domain,
                "status": final_status,
                "session_id": str(session_id) if session_id is not None else None,
                "fetched_count": stats["fetched_count"],
                "parsed_count": stats["parsed_count"],
                "failed_count": stats["failed_count"],
                **self._summarize_error_details(stats["error_summary"]),
            }
        finally:
            self._close_scraper(detail_scraper)
            self._close_scraper(listing_scraper)
            try:
                await client.stop()
            except Exception:
                logger.exception("scheduler.source.client_stop_failed", extra={"domain": domain})
            try:
                self._lease.release(domain, self._worker_id)
            except Exception:
                logger.exception(
                    "scheduler.source.lease_release_failed",
                    extra={"domain": domain, "worker_id": self._worker_id},
                )

    @staticmethod
    def _append_error(
        error_summary: list[dict[str, Any]],
        *,
        code: str,
        message: str,
        error_type: str | None = None,
        sample_url: str | None = None,
    ) -> None:
        error = {
            "code": code,
            "message": message[:500],
        }
        if error_type:
            error["error_type"] = error_type[:100]
        if sample_url:
            error["sample_url"] = sample_url
        error_summary.append(error)

    @staticmethod
    def _summarize_error_details(error_summary: list[dict[str, Any]]) -> dict[str, str]:
        if not error_summary:
            return {}

        first_error = error_summary[0]
        summary: dict[str, str] = {
            "error_message": str(first_error.get("message", ""))[:500],
        }

        error_type = first_error.get("error_type")
        if isinstance(error_type, str) and error_type.strip():
            summary["error_type"] = error_type[:100]

        return summary

    @staticmethod
    def _close_scraper(scraper: Any) -> None:
        if scraper is None:
            return

        close_method = getattr(scraper, "close", None)
        if callable(close_method):
            try:
                close_method()
            except Exception:
                logger.exception(
                    "scheduler.source.scraper_close_failed",
                    extra={"scraper": scraper.__class__.__name__},
                )
            return

        client = getattr(scraper, "client", None)
        if client and hasattr(client, "close"):
            try:
                client.close()
            except Exception:
                logger.exception(
                    "scheduler.source.client_close_failed",
                    extra={"scraper": scraper.__class__.__name__},
                )

    def _list_active_sources(self) -> list[dict[str, Any]]:
        return list(
            self._db["sources"].find(
                {"active": True},
                {"domain": 1, "base_url": 1, "scraper_type": 1, "display_name": 1},
            )
        )


__all__ = [
    "ScrapeOrchestrator",
    "STATIC_SOURCE_REGISTRY",
    "DYNAMIC_SOURCE_REGISTRY",
    "StaticSourceDefinition",
    "DynamicSourceDefinition",
]
