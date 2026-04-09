from __future__ import annotations

import asyncio
import logging

from bs4 import BeautifulSoup

from app.scrapers.base.block_detection import looks_like_blocked
from app.scrapers.base.fallback_metrics import record_fallback_hit
from app.scrapers.base.playwright_client import PlaywrightClient
from app.scrapers.base.static_client import StaticHttpClient
from app.scrapers.base.static_helpers import clean_text
from app.scrapers.yeni_kocaeli.selectors import (
    CONTENT_SELECTORS,
    DATE_SELECTORS,
    TITLE_SELECTORS,
)

logger = logging.getLogger(__name__)


class YeniKocaeliDetailScraper:
    PLAYWRIGHT_TIMEOUT_MS = 12_000

    INVALID_SUMMARY_PHRASES = [
        "en güncel haber sitesi",
    ]

    INVALID_CONTENT_PHRASES = [
    "BENZER HABERLER",
    "Listelenecek haber bulunamadı",
    "UYARI: Bu içeriğe yorum yazarak",
    "Topluluk Kuralları'nı kabul etmiş",
    ]

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

    def fetch_detail_html(self, url: str) -> str:
        try:
            html = self.client.get_text(url)
            if html and not looks_like_blocked(html):
                return html
        except Exception as exc:
            logger.debug(
                "yenikocaeli.detail.static_failed",
                extra={"error": type(exc).__name__},
            )

        try:
            hit_count = record_fallback_hit(
                source="yenikocaeli.com",
                stage="detail",
                fallback="playwright",
            )
            logger.info(
                "scraper.fallback.playwright_used",
                extra={
                    "source": "yenikocaeli.com",
                    "stage": "detail",
                    "hit_count": hit_count,
                },
            )
            html = asyncio.run(
                self._fetch_with_playwright(
                    url=url,
                    wait_for=TITLE_SELECTORS[0],
                    wait_until="networkidle",
                )
            )
            if html and not looks_like_blocked(html):
                return html
        except Exception as exc:
            logger.debug(
                "yenikocaeli.detail.playwright_failed",
                extra={"error": type(exc).__name__},
            )

        raise RuntimeError(f"detail_fetch_failed: {url}")

    def extract_detail_fields(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup)
        summary = self._extract_summary(soup, title)
        content = self._extract_content(soup, title, summary)
        published_at_raw = self._extract_published_at(soup)

        return {
            "title": title,
            "summary": summary,
            "content_text": content,
            "published_at_raw": published_at_raw,
        }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        for selector in TITLE_SELECTORS:
            node = soup.select_one(selector)
            if node:
                text = clean_text(node.get_text(" ", strip=True))
                if text:
                    return text
        return ""

    def _extract_summary(self, soup: BeautifulSoup, title: str) -> str:
        news_node = soup.select_one(".news")
        if not news_node:
            return ""

        paragraphs = [
            clean_text(p.get_text(" ", strip=True))
            for p in news_node.find_all("p")
        ]
        paragraphs = [p for p in paragraphs if p]

        for paragraph in paragraphs:
            lowered = paragraph.lower()

            if paragraph == title:
                continue

            if any(bad in lowered for bad in self.INVALID_SUMMARY_PHRASES):
                continue

            if any(bad.lower() in paragraph.lower() for bad in self.INVALID_CONTENT_PHRASES):
                continue

            return paragraph

        return ""

    def _extract_content(self, soup: BeautifulSoup, title: str, summary: str) -> str:
        for selector in CONTENT_SELECTORS:
            news_node = soup.select_one(selector)
            if not news_node:
                continue

            paragraphs = [
                clean_text(p.get_text(" ", strip=True))
                for p in news_node.find_all(["p", "li"])
            ]
            paragraphs = [p for p in paragraphs if p]

            cleaned_paragraphs: list[str] = []
            for paragraph in paragraphs:
                lowered = paragraph.lower()

                if paragraph == title:
                    continue
                if summary and paragraph == summary:
                    continue
                if paragraph.startswith("Anasayfa"):
                    continue
                if paragraph.startswith("Güncel "):
                    continue
                if any(bad.lower() in lowered for bad in self.INVALID_CONTENT_PHRASES):
                    break

                cleaned_paragraphs.append(paragraph)

            if cleaned_paragraphs:
                return "\n".join(cleaned_paragraphs).strip()

            fallback = clean_text(news_node.get_text(" ", strip=True))
            if fallback and fallback != title and fallback != summary:
                return fallback

        return ""

    def _extract_published_at(self, soup: BeautifulSoup) -> str:
        for selector in DATE_SELECTORS:
            node = soup.select_one(selector)
            if not node:
                continue

            if node.name == "meta":
                content = node.get("content")
                if content:
                    return clean_text(content)

            datetime_value = node.get("datetime")
            if datetime_value:
                return clean_text(datetime_value)

            text_value = clean_text(node.get_text(" ", strip=True))
            if text_value:
                return text_value

        news_node = soup.select_one(".news")
        if news_node:
            text = clean_text(news_node.get_text(" ", strip=True))
            for marker in ["Güncel", "Siyaset", "Ekonomi", "Yaşam", "Sağlık", "Spor"]:
                if marker in text:
                    idx = text.find(marker)
                    snippet = text[idx:idx + 60]
                    return clean_text(snippet)

        return ""

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
