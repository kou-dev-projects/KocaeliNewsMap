from __future__ import annotations

from bs4 import BeautifulSoup

from app.scrapers.base.static_client import StaticHttpClient
from app.scrapers.base.static_helpers import clean_text
from app.scrapers.cagdas_kocaeli.selectors import (
    CONTENT_SELECTORS,
    DATE_SELECTORS,
    IMAGE_SELECTORS,
    TITLE_SELECTORS,
)


class CagdasKocaeliDetailScraper:
    def __init__(self, client: StaticHttpClient | None = None) -> None:
        self.client = client or StaticHttpClient()

    def fetch_detail_html(self, url: str) -> str:
        return self.client.get_text(url)

    def extract_detail_fields(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_text_by_selectors(soup, TITLE_SELECTORS)
        content = self._extract_content(soup)
        published_at_raw = self._extract_published_at(soup)
        image_url = self._extract_image(soup)

        return {
            "title": title,
            "content_text": content,
            "published_at_raw": published_at_raw,
            "image_url": image_url,
        }

    def _extract_text_by_selectors(
        self,
        soup: BeautifulSoup,
        selectors: list[str],
    ) -> str:
        for selector in selectors:
            node = soup.select_one(selector)
            if node:
                return clean_text(node.get_text(" ", strip=True))
        return ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        for selector in CONTENT_SELECTORS:
            node = soup.select_one(selector)
            if node:
                paragraphs = [
                    clean_text(p.get_text(" ", strip=True))
                    for p in node.find_all(["p", "li"])
                ]
                paragraphs = [p for p in paragraphs if p]
                if paragraphs:
                    return "\n".join(paragraphs)

                return clean_text(node.get_text(" ", strip=True))
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
            if text_value and ":" not in text_value:
                return text_value

        return ""

    def _extract_image(self, soup: BeautifulSoup) -> str:
        for selector in IMAGE_SELECTORS:
            node = soup.select_one(selector)
            if not node:
                continue

            if node.name == "meta":
                content = node.get("content")
                if content:
                    return content.strip()

            src = node.get("src")
            if src:
                return src.strip()

        return ""