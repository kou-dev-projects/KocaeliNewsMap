from __future__ import annotations

from dataclasses import dataclass
import logging
from socket import gethostname
from typing import Any, Callable
from uuid import uuid4

from app.scrapers.cagdas_kocaeli.detail import CagdasKocaeliDetailScraper
from app.scrapers.cagdas_kocaeli.listing import CagdasKocaeliListingScraper
from app.scrapers.cagdas_kocaeli.parser import CagdasKocaeliParser
from app.scrapers.ozgur_kocaeli.detail import OzgurKocaeliDetailScraper
from app.scrapers.ozgur_kocaeli.listing import OzgurKocaeliListingScraper
from app.scrapers.ozgur_kocaeli.parser import OzgurKocaeliParser
from app.scrapers.yeni_kocaeli.detail import YeniKocaeliDetailScraper
from app.scrapers.yeni_kocaeli.listing import YeniKocaeliListingScraper
from app.scrapers.yeni_kocaeli.parser import YeniKocaeliParser
from app.services.mcp.server import MCPServer

from .config import SchedulerConfig, load_scheduler_config
from .sessions import CrawlSessionStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StaticSourceDefinition:
    listing_scraper_factory: Callable[[], Any]
    detail_scraper_factory: Callable[[], Any]
    parser_factory: Callable[[], Any]


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


class ScrapeOrchestrator:
    def __init__(
        self,
        *,
        config: SchedulerConfig | None = None,
        database=None,
        mcp_server: MCPServer | None = None,
        session_store: CrawlSessionStore | None = None,
    ) -> None:
        self._config = config or load_scheduler_config()
        if database is None:
            from app.db.database import db as default_db

            self._db = default_db
        else:
            self._db = database
        self._mcp = mcp_server or MCPServer()
        self._sessions = session_store or CrawlSessionStore(self._db)
        self._worker_id = f"scheduler:{gethostname()}"

    def crawl_active_sources(self, *, trigger_type: str = "scheduled") -> dict[str, Any]:
        active_sources = self._list_active_sources()

        summary = {
            "active_sources": len(active_sources),
            "processed_sources": 0,
            "skipped_sources": 0,
            "sessions": [],
        }

        for source_document in active_sources:
            domain = source_document["domain"]
            if domain not in STATIC_SOURCE_REGISTRY:
                logger.info(
                    "scheduler.source.unsupported",
                    extra={"domain": domain, "scraper_type": source_document.get("scraper_type")},
                )
                summary["skipped_sources"] += 1
                continue

            session_result = self._crawl_single_source(
                source_document=source_document,
                trigger_type=trigger_type,
            )
            summary["processed_sources"] += 1
            summary["sessions"].append(session_result)

        return summary

    def crawl_source(self, domain: str, *, trigger_type: str = "manual") -> dict[str, Any]:
        source_document = self._db["sources"].find_one(
            {"domain": domain, "active": True},
            {"domain": 1, "base_url": 1, "scraper_type": 1, "display_name": 1},
        )
        if source_document is None:
            raise ValueError(f"active_source_not_found: {domain}")

        if domain not in STATIC_SOURCE_REGISTRY:
            return {
                "domain": domain,
                "status": "skipped",
                "reason": "unsupported_source",
            }

        return self._crawl_single_source(
            source_document=source_document,
            trigger_type=trigger_type,
        )

    def _crawl_single_source(self, *, source_document: dict[str, Any], trigger_type: str) -> dict[str, Any]:
        domain = source_document["domain"]
        trace_id = uuid4().hex[:16]
        lease = self._mcp.call("acquire_lease", source=domain, worker_id=self._worker_id)
        if not lease.get("acquired", False):
            logger.info(
                "scheduler.source.lease_not_acquired",
                extra={"domain": domain, "worker_id": self._worker_id},
            )
            return {
                "domain": domain,
                "status": "skipped",
                "reason": "lease_not_acquired",
            }

        session_id = self._sessions.create_for_source(
            source_id=source_document["_id"],
            trigger_type=trigger_type,
            lookback_days=self._config.lookback_days,
            worker_version="scheduler_v1",
            trace_id=trace_id,
        )

        stats = {
            "fetched_count": 0,
            "parsed_count": 0,
            "failed_count": 0,
            "error_summary": [],
        }
        definition = STATIC_SOURCE_REGISTRY[domain]
        listing_scraper = definition.listing_scraper_factory()
        detail_scraper = definition.detail_scraper_factory()
        parser = definition.parser_factory()

        try:
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

                    if not record.get("title", "").strip() or not record.get("content_text", "").strip():
                        stats["failed_count"] += 1
                        self._append_error(
                            stats["error_summary"],
                            code="invalid_record",
                            message="Parsed record is missing title or content",
                            sample_url=target_url,
                        )
                        continue

                    write_result = self._mcp.call(
                        "write_news",
                        title=record["title"],
                        url=record["url"],
                        source=record["source_domain"],
                        content=record.get("content_text", ""),
                        summary=record.get("summary", ""),
                        image_url=record.get("image_url", ""),
                        published_at=record.get("published_at_raw", ""),
                        crawl_session_id=str(session_id),
                        resolved_url=record["url"],
                        scraped_at=record.get("scraped_at", ""),
                        parser_version=parser.__class__.__name__,
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
                        sample_url=target_url,
                    )

            final_status = self._sessions.finalize(
                session_id=session_id,
                fetched_count=stats["fetched_count"],
                parsed_count=stats["parsed_count"],
                failed_count=stats["failed_count"],
                error_summary=stats["error_summary"],
            )
            return {
                "domain": domain,
                "status": final_status,
                "session_id": str(session_id),
                "fetched_count": stats["fetched_count"],
                "parsed_count": stats["parsed_count"],
                "failed_count": stats["failed_count"],
            }
        finally:
            self._close_scraper(listing_scraper)
            self._close_scraper(detail_scraper)
            self._mcp.call("release_lease", source=domain, worker_id=self._worker_id)

    @staticmethod
    def _append_error(
        error_summary: list[dict[str, Any]],
        *,
        code: str,
        message: str,
        sample_url: str | None = None,
    ) -> None:
        error = {
            "code": code,
            "message": message[:500],
        }
        if sample_url:
            error["sample_url"] = sample_url
        error_summary.append(error)

    @staticmethod
    def _close_scraper(scraper: Any) -> None:
        client = getattr(scraper, "client", None)
        if client and hasattr(client, "close"):
            client.close()

    def _list_active_sources(self) -> list[dict[str, Any]]:
        return list(
            self._db["sources"].find(
                {"active": True},
                {"domain": 1, "base_url": 1, "scraper_type": 1, "display_name": 1},
            )
        )


__all__ = ["ScrapeOrchestrator", "STATIC_SOURCE_REGISTRY", "StaticSourceDefinition"]
