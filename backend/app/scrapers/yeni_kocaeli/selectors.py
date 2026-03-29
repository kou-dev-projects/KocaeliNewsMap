from __future__ import annotations

BASE_URL = "https://www.yenikocaeli.com"

# Listing
LISTING_NEWS_LINK_SELECTOR = "main a[href*='/haber/'], article a[href*='/haber/'], .news a[href*='/haber/']"
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
    ".news",
    "article",
    ".news-detail-content",
    ".article-content",
    ".entry-content",
    ".post-content",
]

DATE_SELECTORS = [
    "meta[property='article:published_time']",
    "meta[name='datePublished']",
    "meta[name='publish-date']",
    "time",
    ".news-date",
    ".article-date",
    ".publish-date",
    ".date",
]

IMAGE_SELECTORS = [
    "meta[property='og:image']",
    "article img",
    ".news-detail img",
]