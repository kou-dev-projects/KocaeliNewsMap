from __future__ import annotations

from bs4 import BeautifulSoup

from app.scrapers.base.static_client import StaticHttpClient
from app.scrapers.base.static_helpers import clean_text
from app.scrapers.yeni_kocaeli.selectors import (
    CONTENT_SELECTORS,
    DATE_SELECTORS,
    TITLE_SELECTORS,
)


class YeniKocaeliDetailScraper:
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
        self.client = client or StaticHttpClient()

    def fetch_detail_html(self, url: str) -> str:
        return self.client.get_text(url)

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
