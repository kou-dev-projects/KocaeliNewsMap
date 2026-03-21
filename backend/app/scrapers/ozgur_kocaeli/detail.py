from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.scrapers.base.static_client import StaticHttpClient
from app.scrapers.base.static_helpers import clean_text
from app.scrapers.ozgur_kocaeli.selectors import (
    CONTENT_SELECTORS,
    DATE_SELECTORS,
    IMAGE_SELECTORS,
    SUMMARY_SELECTORS,
    TITLE_SELECTORS,
)


PUBLISHED_AT_REGEX = re.compile(
    r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]{3,}\s+\d{4}\s*-\s*\d{2}:\d{2}"
)


class OzgurKocaeliDetailScraper:
    def __init__(self, client: StaticHttpClient | None = None) -> None:
        self.client = client or StaticHttpClient()

    def fetch_detail_html(self, url: str) -> str:
        return self.client.get_text(url)

    def extract_detail_fields(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_text_by_selectors(soup, TITLE_SELECTORS)
        summary = self._extract_summary(soup)
        content = self._extract_content(soup)
        published_at_raw = self._extract_published_at(soup)
        image_url = self._extract_image(soup)

        return {
            "title": title,
            "summary": summary,
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

    def _extract_summary(self, soup: BeautifulSoup) -> str:
        for selector in SUMMARY_SELECTORS:
            node = soup.select_one(selector)
            if node:
                text = clean_text(node.get_text(" ", strip=True))
                if text:
                    return text
        return ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        for selector in CONTENT_SELECTORS:
            node = soup.select_one(selector)
            if not node:
                continue

            paragraphs = [
                clean_text(p.get_text(" ", strip=True))
                for p in node.find_all(["p", "li"])
            ]
            paragraphs = [
                p for p in paragraphs
                if p
                and "Topluluk Kuralları" not in p
                and "Yorumunuz" not in p
                and "hukuki muhatabı" not in p
            ]

            if paragraphs:
                return "\n".join(paragraphs)

            text = clean_text(node.get_text(" ", strip=True))
            if text:
                return text

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

        page_text = soup.get_text(" ", strip=True)
        match = PUBLISHED_AT_REGEX.search(page_text)
        if match:
            return clean_text(match.group(0))

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