# ── Listing ──────────────────────────────────────────
LISTING_LINK = 'a[href*="/haber/"]'

# ── Detail ───────────────────────────────────────────
# Daktilo CMS'de başlık çoğunlukla h1.post-title;
# itemprop="headline" bazen mevcut, bazen değil.
DETAIL_TITLE_SELECTORS = [
    '[itemprop="headline"]',
    "h1.post-title",
    "h1",
]

# İçerik alanı: #main-text veya .post-content
DETAIL_CONTENT_SELECTORS = [
    "#main-text",
    ".post-content",
    "article .content",
    ".entry-content",
]

DETAIL_DATE_META = 'meta[name="datePublished"]'
DETAIL_OG_IMAGE = 'meta[property="og:image"]'

# Gürültü temizleme — haber içeriğinde gereksiz bölümler
NOISE_PATTERNS = [
    r"Daha fazlasını keşfedin",
    r"Yerel ürün sepetleri",
    r"Dijital Gazete Aboneliği",
    r"Şehir rehberi kitapçıkları",
    r"ABONE OL",
    r"Google News",
]