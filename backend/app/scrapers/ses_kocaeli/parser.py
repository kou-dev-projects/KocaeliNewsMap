import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from . import selectors


def clean_content(text: str | None) -> str | None:
    if not text:
        return text

    cleaned = text

    for pattern in selectors.NOISE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.lstrip("-+ ").strip()

    return cleaned


def is_valid_news_url(url: str) -> bool:
    return (
        "/haber/" in url
        and "video" not in url
        and "galeri" not in url
        and "#" not in url
    )


def parse_listing_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []

    for link in soup.select(selectors.LISTING_LINK):
        href = link.get("href")
        if not href:
            continue

        absolute_url = urljoin(base_url, href)

        if not is_valid_news_url(absolute_url):
            continue

        if absolute_url not in urls:
            urls.append(absolute_url)

    return urls


def _select_first(soup: BeautifulSoup, selector_list: list[str]):
    """Birden fazla selector'dan ilk bulunanı döndürür."""
    for sel in selector_list:
        node = soup.select_one(sel)
        if node:
            return node
    return None


def parse_detail(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_el = _select_first(soup, selectors.DETAIL_TITLE_SELECTORS)
    content_el = _select_first(soup, selectors.DETAIL_CONTENT_SELECTORS)
    date_meta = soup.select_one(selectors.DETAIL_DATE_META)
    og_image = soup.select_one(selectors.DETAIL_OG_IMAGE)

    content = content_el.get_text(" ", strip=True) if content_el else None

    result = {
        "url": url,
        "title": title_el.get_text(strip=True) if title_el else None,
        "content": clean_content(content),
        "published_at_raw": date_meta.get("content") if date_meta else None,
        "image_url": og_image.get("content") if og_image else None,
    }

    if not result["title"] or not result["content"]:
        raise ValueError(f"Critical fields missing for detail page: {url}")

    return result