import asyncio
import logging

from app.scrapers.base.block_detection import looks_like_blocked
from app.scrapers.base.fallback_metrics import record_fallback_hit
from app.scrapers.base.playwright_client import PlaywrightClient
from app.scrapers.base.robots import RobotsChecker
from app.scrapers.base.static_client import StaticHttpClient
from app.settings import settings

from .parser import parse_listing_links

logger = logging.getLogger(__name__)


class BizimYakaListingScraper:
    def __init__(self, client: PlaywrightClient, listing_url: str):
        self.client = client
        self.listing_url = listing_url
        self.robots = RobotsChecker(strict=False)
        self.static_client = StaticHttpClient(timeout=15, delay_seconds=0.2)

    async def fetch_links(self) -> list[str]:
        allowed, reason = self.robots.can_fetch(self.listing_url)

        if not allowed:
            raise PermissionError(reason)

        if "could not be verified" in reason:
            logger.warning("robots.warning", extra={"reason": reason})

        # 1) Static HTTP — hızlı, hafif
        try:
            html = await asyncio.to_thread(
                self.static_client.get_text, self.listing_url
            )
            if html and not looks_like_blocked(html):
                urls = parse_listing_links(html=html, base_url=self.listing_url)
                if urls:
                    return urls
        except Exception as exc:
            logger.debug("bizimyaka.listing.static_failed", extra={"error": str(exc)[:100]})

        # 2) Playwright fallback — JS render gerekirse
        if not settings.playwright_fallback_enabled:
            logger.info(
                "scraper.fallback.playwright_disabled",
                extra={"source": "bizimyaka.com", "stage": "listing"},
            )
            raise RuntimeError("listing_fetch_failed_playwright_disabled")

        hit_count = record_fallback_hit(
            source="bizimyaka.com",
            stage="listing",
            fallback="playwright",
        )
        logger.info(
            "scraper.fallback.playwright_used",
            extra={
                "source": "bizimyaka.com",
                "stage": "listing",
                "hit_count": hit_count,
            },
        )
        try:
            html = await self.client.get_html(url=self.listing_url)
            if html and not looks_like_blocked(html):
                return parse_listing_links(html=html, base_url=self.listing_url)
        except Exception as exc:
            logger.debug("bizimyaka.listing.playwright_failed", extra={"error": str(exc)[:100]})

        raise RuntimeError("listing_fetch_failed")

    def close(self) -> None:
        self.static_client.close()