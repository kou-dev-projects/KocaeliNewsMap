from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


def make_news_tools(write_service, lease_service):
  

    def write_news(
        title: str,
        url: str,
        source: str,
        content: str = "",
        summary: str = "",
        image_url: str = "",
        published_at: str = "",
        crawl_session_id: str = "",
        resolved_url: str = "",
        scraped_at: str = "",
        parser_version: str = "mcp_write_v1",
    ) -> dict[str, Any]:
      
        from app.services.mcp.schemas import NewsWriteRequest

        request = NewsWriteRequest(
            title=title,
            url=url,
            source=source,
            content=content or None,
            summary=summary or None,
            image_url=image_url or None,
            published_at=published_at or None,
            crawl_session_id=crawl_session_id or None,
            resolved_url=resolved_url or None,
            scraped_at=scraped_at or None,
            parser_version=parser_version,
        )

        result = write_service.write(request)

        logger.info(
            "mcp.tool.write_news",
            extra={
                "status": result.status.value,
                "was_duplicate": result.was_duplicate,
                "news_id": result.news_id,
            },
        )

        return {
            "status": result.status.value,
            "news_id": result.news_id,
            "was_duplicate": result.was_duplicate,
            "reason": result.reason,
        }

    def acquire_lease(source: str, worker_id: str) -> dict[str, Any]:
       
        acquired = lease_service.acquire(source, worker_id)
        return {
            "acquired": acquired,
            "source": source,
            "worker_id": worker_id,
        }

    def release_lease(source: str, worker_id: str) -> dict[str, Any]:
        """Scraping tamamlandığında kilidi bırak."""
        released = lease_service.release(source, worker_id)
        return {"released": released, "source": source}

    def check_lease(source: str) -> dict[str, Any]:
        """Kaynak kilitli mi? Hangi worker tutuyor?"""
        info = lease_service.get_info(source)
        if info is None:
            return {"held": False, "source": source}
        return {
            "held": True,
            "source": source,
            "worker_id": info.worker_id,
            "ttl_seconds": info.ttl_seconds,
        }

    def get_queue_status() -> dict[str, Any]:
        
        return {
            "queue_size": write_service._queue.size,
            "dead_letter_size": write_service._dead_letter.size,
        }

    return {
        "write_news": write_news,
        "acquire_lease": acquire_lease,
        "release_lease": release_lease,
        "check_lease": check_lease,
        "get_queue_status": get_queue_status,
    }
