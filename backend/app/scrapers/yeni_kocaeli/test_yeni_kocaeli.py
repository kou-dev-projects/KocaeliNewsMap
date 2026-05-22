from __future__ import annotations

from app.scrapers.yeni_kocaeli.parser import YeniKocaeliParser


def test_build_record_returns_expected_fields() -> None:
    parser = YeniKocaeliParser()

    detail_data = {
        "title": "Örnek Başlık",
        "summary": "Örnek özet",
        "content_text": "Örnek içerik",
        "published_at_raw": "2026-03-21T01:39:00+03:00",
    }

    record = parser.build_record(
        "https://www.yenikocaeli.com/haber/123/ornek-haber",
        detail_data,
    )

    assert record["source_domain"] == "yenikocaeli.com"
    assert record["title"] == "Örnek Başlık"
    assert record["summary"] == "Örnek özet"
    assert record["content_text"] == "Örnek içerik"
    assert record["published_at_raw"] == "2026-03-21T01:39:00+03:00"
    assert record["url"] == "https://www.yenikocaeli.com/haber/123/ornek-haber"
    assert "scraped_at" in record