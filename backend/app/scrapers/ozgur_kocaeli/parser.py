from __future__ import annotations

from datetime import datetime, timezone

from app.scrapers.base.static_helpers import normalize_url
from app.scrapers.ozgur_kocaeli.selectors import BASE_URL


class OzgurKocaeliParser:
    SOURCE_DOMAIN = "ozgurkocaeli.com.tr"
    SOURCE_NAME = "Özgür Kocaeli"

    def build_record(self, url: str, detail_data: dict) -> dict:
        return {
            "source_domain": self.SOURCE_DOMAIN,
            "source_name": self.SOURCE_NAME,
            "source_base_url": BASE_URL,
            "url": normalize_url(url),
            "title": detail_data.get("title", ""),
            "summary": detail_data.get("summary", ""),
            "content_text": detail_data.get("content_text", ""),
            "published_at_raw": detail_data.get("published_at_raw", ""),
            "image_url": detail_data.get("image_url", ""),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }