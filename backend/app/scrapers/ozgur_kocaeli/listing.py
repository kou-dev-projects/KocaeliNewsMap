from __future__ import annotations

from bs4 import BeautifulSoup

from app.scrapers.base.static_client import StaticHttpClient
from app.scrapers.base.static_helpers import to_absolute_url, unique_urls
from app.scrapers.ozgur_kocaeli.selectors import (
    BASE_URL,
    LISTING_NEWS_LINK_SELECTOR,
    LISTING_NEWS_URL_KEYWORD,
)


class OzgurKocaeliListingScraper:
    def __init__(self, client: StaticHttpClient | None = None) -> None:
        self.client = client or StaticHttpClient()

    def fetch_listing_html(self, url: str) -> str:
        return self.client.get_text(url)

    def extract_news_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls: list[str] = []

        for a_tag in soup.select(LISTING_NEWS_LINK_SELECTOR):
            href = a_tag.get("href")
            if not href:
                continue

            absolute_url = to_absolute_url(BASE_URL, href)

            if LISTING_NEWS_URL_KEYWORD not in absolute_url:
                continue

            urls.append(absolute_url)

        return unique_urls(urls)