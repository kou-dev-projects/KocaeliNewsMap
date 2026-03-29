from __future__ import annotations

BASE_URL = "https://www.cagdaskocaeli.com.tr"

# Listing
LISTING_NEWS_LINK_SELECTOR = "a[href]"
LISTING_NEWS_URL_KEYWORD = "/haber/"

# Detail
TITLE_SELECTORS = [
    "h1",
    "h1.entry-title",
    ".news-title h1",
    ".article-title h1",
]

CONTENT_SELECTORS = [
    ".news-detail-content",
    ".article-content",
    ".entry-content",
    ".post-content",
    "article",
]

DATE_SELECTORS = [
    "meta[property='article:published_time']",
    "meta[name='datePublished']",
    "meta[name='publish-date']",
    ".news-date",
    ".article-date",
    ".publish-date",
    ".date",
    "time",
]

IMAGE_SELECTORS = [
    "meta[property='og:image']",
    ".news-detail img",
    "article img",
]