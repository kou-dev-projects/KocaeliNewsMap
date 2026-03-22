
from app.scrapers.cagdas_kocaeli.listing import CagdasKocaeliListingScraper
from app.scrapers.cagdas_kocaeli.detail import CagdasKocaeliDetailScraper
from app.scrapers.cagdas_kocaeli.parser import CagdasKocaeliParser

from app.scrapers.ozgur_kocaeli.listing import OzgurKocaeliListingScraper
from app.scrapers.ozgur_kocaeli.detail import OzgurKocaeliDetailScraper
from app.scrapers.ozgur_kocaeli.parser import OzgurKocaeliParser

from app.scrapers.yeni_kocaeli.listing import YeniKocaeliListingScraper
from app.scrapers.yeni_kocaeli.detail import YeniKocaeliDetailScraper
from app.scrapers.yeni_kocaeli.parser import YeniKocaeliParser

from app.services.ner.config import load_ner_config
from app.services.ner.factory import build_ner_service
from app.services.ner.schemas import NERInput


def short(text: str, limit: int = 180) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text[:limit] + ("..." if len(text) > limit else "")


def entity_preview(result) -> list[str]:
    out = []
    for ent in result.raw_entities[:6]:
        out.append(f"{ent.label}:{ent.text}:{ent.score:.2f}")
    return out


sources = [
    (
        "cagdaskocaeli",
        "https://www.cagdaskocaeli.com.tr",
        CagdasKocaeliListingScraper(),
        CagdasKocaeliDetailScraper(),
        CagdasKocaeliParser(),
    ),
    (
        "ozgurkocaeli",
        "https://www.ozgurkocaeli.com.tr",
        OzgurKocaeliListingScraper(),
        OzgurKocaeliDetailScraper(),
        OzgurKocaeliParser(),
    ),
    (
        "yenikocaeli",
        "https://www.yenikocaeli.com",
        YeniKocaeliListingScraper(),
        YeniKocaeliDetailScraper(),
        YeniKocaeliParser(),
    ),
]

ner = build_ner_service(load_ner_config())

print("=" * 120)
print("[REAL SCRAPER -> PARSER -> NER]")
print("=" * 120)

for source_name, source_url, listing_scraper, detail_scraper, parser in sources:
    print(f"\n### SOURCE: {source_name}")

    try:
        listing_html = listing_scraper.fetch_listing_html(source_url)
        urls = listing_scraper.extract_news_urls(listing_html)
        print(f"listing_html_len={len(listing_html)}")
        print(f"extracted_urls={len(urls)}")
    except Exception as exc:
        print(f"LISTING_FAIL: {type(exc).__name__}: {exc}")
        continue

    if not urls:
        print("NO_URLS_FOUND")
        continue

    for idx, url in enumerate(urls[:3], start=1):
        print(f"\n  [{idx}] URL: {url}")

        try:
            detail_html = detail_scraper.fetch_detail_html(url)
            detail_data = detail_scraper.extract_detail_fields(detail_html)
            record = parser.build_record(url, detail_data)
        except Exception as exc:
            print(f"  DETAIL_FAIL: {type(exc).__name__}: {exc}")
            continue

        title = (record.get("title") or "").strip()
        content = (record.get("content_text") or "").strip()
        published = (record.get("published_at_raw") or "").strip()

        print(f"  title={short(title, 120)}")
        print(f"  published={published}")
        print(f"  content_len={len(content)}")
        print(f"  content={short(content, 220)}")

        if not title and not content:
            print("  EMPTY_PARSE")
            continue

        try:
            result = ner.extract_locations(
                NERInput(
                    title=title,
                    content=content,
                )
            )
            print(f"  validated_districts={result.validated_districts}")
            print(f"  raw_entities={entity_preview(result)}")
        except Exception as exc:
            print(f"  NER_FAIL: {type(exc).__name__}: {exc}")

print("\nDone.")
