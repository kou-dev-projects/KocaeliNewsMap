import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin


NOISE_PATTERNS = [
    r"Daha fazlasını keşfedin",
    r"Yerel ürün sepetleri",
    r"Dijital Gazete Aboneliği",
    r"Şehir rehberi kitapçıkları",
]

def clean_content(text: str | None) -> str | None:
    if not text:
        return text

    cleaned = text

    for pattern in NOISE_PATTERNS:
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

    for link in soup.select('a[href*="/haber/"]'):
        href = link.get("href")
        if not href:
            continue

        absolute_url = urljoin(base_url, href)

        if not is_valid_news_url(absolute_url):
            continue

        if absolute_url not in urls:
            urls.append(absolute_url)

    return urls


def parse_detail(html: str, url: str) -> dict:
    from . import selectors

    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one(selectors.DETAIL_TITLE)
    content_el = soup.select_one(selectors.DETAIL_CONTENT)
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