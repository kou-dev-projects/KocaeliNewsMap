from __future__ import annotations

import asyncio
import re
import logging

from bs4 import BeautifulSoup

from app.scrapers.base.block_detection import looks_like_blocked
from app.scrapers.base.fallback_metrics import record_fallback_hit
from app.scrapers.base.playwright_client import PlaywrightClient
from app.scrapers.base.static_client import StaticHttpClient
from app.scrapers.base.static_helpers import to_absolute_url, unique_urls
from app.scrapers.yeni_kocaeli.selectors import (
    BASE_URL,
    LISTING_NEWS_LINK_SELECTOR,
)


DETAIL_NEWS_PATTERN = re.compile(r"^https://www\.yenikocaeli\.com/haber/.+/\d+\.html$")
logger = logging.getLogger(__name__)


class YeniKocaeliListingScraper:
    PLAYWRIGHT_TIMEOUT_MS = 12_000

    def __init__(self, client: StaticHttpClient | None = None) -> None:
        self.client = client or StaticHttpClient(
            timeout=8,
            delay_seconds=0.2,
            retry_total=0,
            retry_connect=0,
            retry_read=0,
            retry_status=0,
        )
        self.playwright_client_factory = PlaywrightClient

    def fetch_listing_html(self, url: str) -> str:
        try:
            html = self.client.get_text(url)
            if html and not looks_like_blocked(html):
                return html
        except Exception as exc:
            logger.debug(
                "yenikocaeli.listing.static_failed",
                extra={"error": type(exc).__name__},
            )

        try:
            hit_count = record_fallback_hit(
                source="yenikocaeli.com",
                stage="listing",
                fallback="playwright",
            )
            logger.info(
                "scraper.fallback.playwright_used",
                extra={
                    "source": "yenikocaeli.com",
                    "stage": "listing",
                    "hit_count": hit_count,
                },
            )
            html = asyncio.run(
                self._fetch_with_playwright(
                    url=url,
                    wait_for=LISTING_NEWS_LINK_SELECTOR,
                    wait_until="networkidle",
                )
            )
            if html and not looks_like_blocked(html):
                return html
        except Exception as exc:
            logger.debug(
                "yenikocaeli.listing.playwright_failed",
                extra={"error": type(exc).__name__},
            )

        raise RuntimeError("listing_fetch_failed")

    def extract_news_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls: list[str] = []

        for a_tag in soup.select(LISTING_NEWS_LINK_SELECTOR):
            href = a_tag.get("href")
            if not href:
                continue

            absolute_url = to_absolute_url(BASE_URL, href)

            if not DETAIL_NEWS_PATTERN.match(absolute_url):
                continue

            urls.append(absolute_url)

        return unique_urls(urls)

    def close(self) -> None:
        self.client.close()

    async def _fetch_with_playwright(
        self,
        *,
        url: str,
        wait_for: str,
        wait_until: str,
    ) -> str:
        client = self.playwright_client_factory(
            headless=True,
            timeout_ms=self.PLAYWRIGHT_TIMEOUT_MS,
        )
        try:
            return await client.get_html(url=url, wait_for=wait_for, wait_until=wait_until)
        finally:
            await client.stop()
