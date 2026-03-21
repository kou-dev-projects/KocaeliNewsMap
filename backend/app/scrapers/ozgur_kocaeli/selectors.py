from __future__ import annotations

BASE_URL = "https://www.ozgurkocaeli.com.tr"

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

SUMMARY_SELECTORS = [
    "h1 + p",
    ".news-description",
    ".article-spot",
    ".spot",
    ".description",
]

CONTENT_SELECTORS = [
    "article",
    ".news-detail-content",
    ".article-content",
    ".entry-content",
    ".post-content",
]

DATE_SELECTORS = [
    "meta[property='article:published_time']",
    "meta[name='datePublished']",
    "time",
]

IMAGE_SELECTORS = [
    "meta[property='og:image']",
    "article img",
    ".news-detail img",
]