import asyncio
import logging

from app.scrapers.base.block_detection import looks_like_blocked
from app.scrapers.base.fallback_metrics import record_fallback_hit
from app.scrapers.base.playwright_client import PlaywrightClient
from app.scrapers.base.static_client import StaticHttpClient
from app.settings import settings

from .parser import parse_detail
from .selectors import DETAIL_TITLE

logger = logging.getLogger(__name__)


class BizimYakaDetailScraper:
    def __init__(self, client: PlaywrightClient):
        self.client = client
        self.static_client = StaticHttpClient(
            timeout=10,
            delay_seconds=0.2,
            retry_total=0,
            retry_connect=0,
            retry_read=0,
            retry_status=0,
        )

    async def fetch_detail(self, url: str) -> dict:
        # 1) Static HTTP — hızlı, hafif
        try:
            html = await asyncio.to_thread(self.static_client.get_text, url)
            if html and not looks_like_blocked(html):
                return parse_detail(html=html, url=url)
        except Exception:
            pass

        # 2) Playwright fallback
        if not settings.playwright_fallback_enabled:
            logger.info(
                "scraper.fallback.playwright_disabled",
                extra={"source": "bizimyaka.com", "stage": "detail"},
            )
            raise RuntimeError(f"detail_fetch_failed_playwright_disabled: {url}")

        hit_count = record_fallback_hit(
            source="bizimyaka.com",
            stage="detail",
            fallback="playwright",
        )
        logger.info(
            "scraper.fallback.playwright_used",
            extra={
                "source": "bizimyaka.com",
                "stage": "detail",
                "hit_count": hit_count,
            },
        )
        try:
            html = await self.client.get_html(
                url=url,
                wait_for=DETAIL_TITLE,
            )
            if html and not looks_like_blocked(html):
                return parse_detail(html=html, url=url)
        except Exception:
            pass

        raise RuntimeError(f"detail_fetch_failed: {url}")

    def close(self) -> None:
        self.static_client.close()
