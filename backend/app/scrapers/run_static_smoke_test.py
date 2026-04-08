from __future__ import annotations

from app.scrapers.base.date_utils import is_within_last_n_days
from app.scrapers.cagdas_kocaeli.detail import CagdasKocaeliDetailScraper
from app.scrapers.cagdas_kocaeli.listing import CagdasKocaeliListingScraper
from app.scrapers.cagdas_kocaeli.parser import CagdasKocaeliParser
from app.scrapers.ozgur_kocaeli.detail import OzgurKocaeliDetailScraper
from app.scrapers.ozgur_kocaeli.listing import OzgurKocaeliListingScraper
from app.scrapers.ozgur_kocaeli.parser import OzgurKocaeliParser
from app.scrapers.yeni_kocaeli.detail import YeniKocaeliDetailScraper
from app.scrapers.yeni_kocaeli.listing import YeniKocaeliListingScraper
from app.scrapers.yeni_kocaeli.parser import YeniKocaeliParser


def shorten(text: str, limit: int = 180) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def run_source(
    name: str,
    source_url: str,
    listing_scraper,
    detail_scraper,
    parser,
) -> None:
    print(f"\n===== {name} =====")

    listing_html = listing_scraper.fetch_listing_html(source_url)
    urls = listing_scraper.extract_news_urls(listing_html)

    print(f"Bulunan link sayısı: {len(urls)}")

    if not urls:
        print("Link bulunamadı.")
        return

    selected_record = None
    selected_url = None

    for target_url in urls[:10]:
        try:
            detail_html = detail_scraper.fetch_detail_html(target_url)
            detail_data = detail_scraper.extract_detail_fields(detail_html)
            record = parser.build_record(target_url, detail_data)

            has_title = bool(record.get("title", "").strip())
            has_content = bool(record.get("content_text", "").strip())

            if has_title and has_content:
                selected_record = record
                selected_url = target_url
                break

        except Exception as exc:
            print(f"Hata ({target_url}): {exc}")

    if not selected_record:
        print("Geçerli haber detayı bulunamadı.")
        return

    print(f"Seçilen link: {selected_url}")
    print(f"Başlık: {selected_record.get('title', '')}")
    print(f"Tarih (raw): {selected_record.get('published_at_raw', '')}")
    print(f"Son 1 gün: {is_within_last_n_days(selected_record.get('published_at_raw'), 1)}")
    print(f"Son 2 gün: {is_within_last_n_days(selected_record.get('published_at_raw'), 2)}")
    print(f"Son 3 gün: {is_within_last_n_days(selected_record.get('published_at_raw'), 3)}")

    if "summary" in selected_record:
        print(f"Özet: {shorten(selected_record.get('summary', ''))}")

    print(f"İçerik: {shorten(selected_record.get('content_text', ''))}")

def main() -> None:
    run_source(
        name="Çağdaş Kocaeli",
        source_url="https://www.cagdaskocaeli.com.tr",
        listing_scraper=CagdasKocaeliListingScraper(),
        detail_scraper=CagdasKocaeliDetailScraper(),
        parser=CagdasKocaeliParser(),
    )

    run_source(
        name="Özgür Kocaeli",
        source_url="https://www.ozgurkocaeli.com.tr",
        listing_scraper=OzgurKocaeliListingScraper(),
        detail_scraper=OzgurKocaeliDetailScraper(),
        parser=OzgurKocaeliParser(),
    )

    run_source(
        name="Yeni Kocaeli",
        source_url="https://www.yenikocaeli.com",
        listing_scraper=YeniKocaeliListingScraper(),
        detail_scraper=YeniKocaeliDetailScraper(),
        parser=YeniKocaeliParser(),
    )


if __name__ == "__main__":
    main()