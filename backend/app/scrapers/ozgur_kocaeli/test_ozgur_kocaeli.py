from __future__ import annotations

from app.scrapers.ozgur_kocaeli.detail import OzgurKocaeliDetailScraper
from app.scrapers.ozgur_kocaeli.parser import OzgurKocaeliParser


def test_build_record_returns_expected_fields() -> None:
    parser = OzgurKocaeliParser()

    detail_data = {
        "title": "Örnek Başlık",
        "summary": "Örnek özet",
        "content_text": "Örnek içerik",
        "published_at_raw": "2026-03-21T01:39:00+03:00",
    }

    record = parser.build_record(
        "https://www.ozgurkocaeli.com.tr/haber/123/ornek-haber",
        detail_data,
    )

    assert record["source_domain"] == "ozgurkocaeli.com.tr"
    assert record["title"] == "Örnek Başlık"
    assert record["summary"] == "Örnek özet"
    assert record["content_text"] == "Örnek içerik"
    assert record["published_at_raw"] == "2026-03-21T01:39:00+03:00"
    assert record["url"] == "https://www.ozgurkocaeli.com.tr/haber/123/ornek-haber"
    assert "scraped_at" in record


def test_detail_uses_summary_as_content_when_content_is_empty() -> None:
        scraper = OzgurKocaeliDetailScraper()
        html = """
        <html>
            <head>
                <meta property='article:published_time' content='2026-04-07T10:00:00+03:00'>
            </head>
            <body>
                <h1>Ornek Baslik</h1>
                <p>Bu paragraf haberin asil govdesidir ve yirmi karakterden uzundur.</p>
                <p>06 Nis 2026 - 15:30 - Spor --- Okunma Yazdir</p>
            </body>
        </html>
        """

        result = scraper.extract_detail_fields(html)

        assert result["title"] == "Ornek Baslik"
        assert result["summary"] == "Bu paragraf haberin asil govdesidir ve yirmi karakterden uzundur."
        assert result["content_text"] == result["summary"]


def test_detail_keeps_content_when_valid_paragraph_exists() -> None:
        scraper = OzgurKocaeliDetailScraper()
        html = """
        <html>
            <body>
                <h1>Ornek Baslik</h1>
                <p>Bu paragraf ozet olarak secilecek kadar uzundur ve ilk satirdir.</p>
                <p>Bu ikinci paragraf asıl iceriktir ve kaydedilmelidir.</p>
                <p>Topluluk Kurallari</p>
            </body>
        </html>
        """

        result = scraper.extract_detail_fields(html)

        assert result["summary"] == "Bu paragraf ozet olarak secilecek kadar uzundur ve ilk satirdir."
        assert result["content_text"] == "Bu ikinci paragraf asıl iceriktir ve kaydedilmelidir."