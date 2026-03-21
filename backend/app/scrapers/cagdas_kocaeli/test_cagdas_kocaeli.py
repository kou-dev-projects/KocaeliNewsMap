from __future__ import annotations

from app.scrapers.cagdas_kocaeli.parser import CagdasKocaeliParser


def test_build_record_returns_expected_fields() -> None:
    parser = CagdasKocaeliParser()

    detail_data = {
        "title": "Örnek Başlık",
        "content_text": "Örnek içerik",
        "published_at_raw": "21.03.2026",
        "image_url": "https://example.com/image.jpg",
    }

    record = parser.build_record(
        "https://www.cagdaskocaeli.com.tr/haber/ornek-haber",
        detail_data,
    )

    assert record["source_domain"] == "cagdaskocaeli.com.tr"
    assert record["title"] == "Örnek Başlık"
    assert record["content_text"] == "Örnek içerik"
    assert record["published_at_raw"] == "21.03.2026"
    assert record["image_url"] == "https://example.com/image.jpg"
    assert record["url"] == "https://www.cagdaskocaeli.com.tr/haber/ornek-haber"
    assert "scraped_at" in record