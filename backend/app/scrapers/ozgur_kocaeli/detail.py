from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.scrapers.base.static_client import StaticHttpClient
from app.scrapers.base.static_helpers import clean_text
from app.scrapers.ozgur_kocaeli.selectors import (
    DATE_SELECTORS,
    TITLE_SELECTORS,
)


PUBLISHED_AT_REGEX = re.compile(
    r"\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]{3,}\s+\d{4}\s*-\s*\d{2}:\d{2}"
)


class OzgurKocaeliDetailScraper:
    INVALID_CONTENT_PHRASES = [
    "Topluluk Kuralları",
    "Yorum yazarak",
    "Yazılan yorumlardan",
    "Haber ajansları tarafından servis edilen",
    "Yorumunuz gözden geçirilip yayınlanacaktır",
    "Mahreç",
    "Okunma",
    "Yazdır",
    "Son bir ayda ozgurkocaeli.com.tr sitesinde",
    "Yorumunuz yarım kaldı",
    "Kırmızı alanlar eksik veya hatalı girildi",
    "Yorumunuz için teşekkürler",
    ]

    def __init__(self, client: StaticHttpClient | None = None) -> None:
        self.client = client or StaticHttpClient()

    def fetch_detail_html(self, url: str) -> str:
        return self.client.get_text(url)

    def extract_detail_fields(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup)
        summary = self._extract_summary(soup, title)
        content = self._extract_content(soup, title, summary)
        if not content and summary:
            # Some pages render the full article as the first paragraph and
            # footer/comment blocks immediately after it. In that shape,
            # summary is the only clean article text.
            content = summary
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
        paragraphs = [
            clean_text(p.get_text(" ", strip=True))
            for p in soup.find_all("p")
        ]
        paragraphs = [p for p in paragraphs if p]

        for paragraph in paragraphs:
            lowered = paragraph.lower()

            if paragraph == title:
                continue
            if any(bad.lower() in lowered for bad in self.INVALID_CONTENT_PHRASES):
                continue
            if len(paragraph) < 25:
                continue

            return paragraph

        return ""

    def _extract_content(self, soup: BeautifulSoup, title: str, summary: str) -> str:
        paragraphs = [
            clean_text(p.get_text(" ", strip=True))
            for p in soup.find_all("p")
        ]
        paragraphs = [p for p in paragraphs if p]

        cleaned_paragraphs: list[str] = []
        for paragraph in paragraphs:
            lowered = paragraph.lower()

            if paragraph == title:
                continue
            if summary and paragraph == summary:
                continue
            if len(paragraph) < 20:
                continue
            
            if any(bad.lower() in lowered for bad in self.INVALID_CONTENT_PHRASES):
                break

            cleaned_paragraphs.append(paragraph)

        return "\n".join(cleaned_paragraphs).strip()

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
