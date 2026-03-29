import asyncio
import logging

from app.scrapers.base.block_detection import looks_like_blocked
from app.scrapers.base.crawl_api_client import CrawlApiClient
from app.scrapers.base.fallback_metrics import record_fallback_hit
from app.scrapers.base.playwright_client import PlaywrightClient
from app.scrapers.base.robots import RobotsChecker
from app.scrapers.base.static_client import StaticHttpClient
from app.settings import settings

from .parser import parse_listing_links

logger = logging.getLogger(__name__)


class SesKocaeliListingScraper:
    def __init__(self, client: PlaywrightClient, listing_url: str):
        self.client = client
        self.listing_url = listing_url
        self.robots = RobotsChecker(strict=False)
        self.crawl_api = CrawlApiClient()
        self.static_client = StaticHttpClient(timeout=15, delay_seconds=0.2)

    async def fetch_links(self) -> list[str]:
        allowed, reason = self.robots.can_fetch(self.listing_url)

        if not allowed:
            raise PermissionError(reason)

        if "could not be verified" in reason:
            logger.warning("robots.warning", extra={"reason": reason})

        # 1) Static HTTP — hızlı, hafif
        try:
            html = await asyncio.to_thread(self.static_client.get_text, self.listing_url)
            if html and not looks_like_blocked(html):
                urls = parse_listing_links(html=html, base_url=self.listing_url)
                if urls:
                    return urls
        except Exception:
            pass

        # 2) Playwright fallback
        if settings.playwright_fallback_enabled:
            hit_count = record_fallback_hit(
                source="seskocaeli.com",
                stage="listing",
                fallback="playwright",
            )
            logger.info(
                "scraper.fallback.playwright_used",
                extra={
                    "source": "seskocaeli.com",
                    "stage": "listing",
                    "hit_count": hit_count,
                },
            )
            try:
                html = await self.client.get_html(url=self.listing_url)
                if html and not looks_like_blocked(html):
                    urls = parse_listing_links(html=html, base_url=self.listing_url)
                    if urls:
                        return urls
            except Exception:
                pass
        else:
            logger.info(
                "scraper.fallback.playwright_disabled",
                extra={"source": "seskocaeli.com", "stage": "listing"},
            )

        # 3) CrawlAPI (ScrapingBee/Cloudflare) — son çare
        if not self.crawl_api.enabled:
            raise RuntimeError("listing_fetch_failed")

        crawl_hit_count = record_fallback_hit(
            source="seskocaeli.com",
            stage="listing",
            fallback="crawl_api",
        )
        logger.info(
            "scraper.fallback.crawl_api_used",
            extra={
                "source": "seskocaeli.com",
                "stage": "listing",
                "hit_count": crawl_hit_count,
            },
        )

        html = await asyncio.to_thread(self.crawl_api.fetch_html, self.listing_url)
        if looks_like_blocked(html):
            raise RuntimeError("cloudflare_challenge_detected")

        return parse_listing_links(html=html, base_url=self.listing_url)

    def close(self) -> None:
        self.static_client.close()