import asyncio
import logging

from app.scrapers.base.block_detection import looks_like_blocked
from app.scrapers.base.crawl_api_client import CrawlApiClient
from app.scrapers.base.fallback_metrics import record_fallback_hit
from app.scrapers.base.playwright_client import PlaywrightClient
from app.scrapers.base.static_client import StaticHttpClient
from app.settings import settings

from .parser import parse_detail
from .selectors import DETAIL_TITLE_SELECTORS

logger = logging.getLogger(__name__)

_PLAYWRIGHT_WAIT_FOR = DETAIL_TITLE_SELECTORS[0]


class SesKocaeliDetailScraper:
    def __init__(self, client: PlaywrightClient):
        self.client = client
        self.crawl_api = CrawlApiClient()
        self.static_client = StaticHttpClient(timeout=15, delay_seconds=0.2)

    async def fetch_detail(self, url: str) -> dict:
        # 1) Static HTTP — hızlı, hafif
        try:
            html = await asyncio.to_thread(self.static_client.get_text, url)
            if html and not looks_like_blocked(html):
                return parse_detail(html=html, url=url)
        except Exception:
            pass

        # 2) Playwright fallback
        html = ""
        if settings.playwright_fallback_enabled:
            hit_count = record_fallback_hit(
                source="seskocaeli.com",
                stage="detail",
                fallback="playwright",
            )
            logger.info(
                "scraper.fallback.playwright_used",
                extra={
                    "source": "seskocaeli.com",
                    "stage": "detail",
                    "hit_count": hit_count,
                },
            )
            try:
                html = await self.client.get_html(
                    url=url,
                    wait_for=_PLAYWRIGHT_WAIT_FOR,
                )
            except Exception:
                try:
                    html = await self.client.get_html(url=url)
                except Exception:
                    html = ""
        else:
            logger.info(
                "scraper.fallback.playwright_disabled",
                extra={"source": "seskocaeli.com", "stage": "detail"},
            )

        if html and not looks_like_blocked(html):
            try:
                return parse_detail(html=html, url=url)
            except Exception:
                pass

        # 3) CrawlAPI — son çare
        if not self.crawl_api.enabled:
            raise RuntimeError(f"detail_fetch_failed: {url}")

        crawl_hit_count = record_fallback_hit(
            source="seskocaeli.com",
            stage="detail",
            fallback="crawl_api",
        )
        logger.info(
            "scraper.fallback.crawl_api_used",
            extra={
                "source": "seskocaeli.com",
                "stage": "detail",
                "hit_count": crawl_hit_count,
            },
        )

        html = await asyncio.to_thread(self.crawl_api.fetch_html, url)
        if looks_like_blocked(html):
            raise RuntimeError("cloudflare_challenge_detected")

        return parse_detail(html=html, url=url)

    def close(self) -> None:
        self.static_client.close()
