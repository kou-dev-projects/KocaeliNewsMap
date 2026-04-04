from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.scrapers.cagdas_kocaeli.detail import CagdasKocaeliDetailScraper
from app.scrapers.cagdas_kocaeli.listing import CagdasKocaeliListingScraper
from app.scrapers.cagdas_kocaeli.parser import CagdasKocaeliParser
from app.scrapers.ozgur_kocaeli.detail import OzgurKocaeliDetailScraper
from app.scrapers.ozgur_kocaeli.listing import OzgurKocaeliListingScraper
from app.scrapers.ozgur_kocaeli.parser import OzgurKocaeliParser
from app.scrapers.yeni_kocaeli.detail import YeniKocaeliDetailScraper
from app.scrapers.yeni_kocaeli.listing import YeniKocaeliListingScraper
from app.scrapers.yeni_kocaeli.parser import YeniKocaeliParser
from app.services.geocoding.config import GeocodingConfig
from app.services.geocoding.factory import build_geocoding_service
from app.services.geocoding.schemas import GeocodingFailure, GeocodingInput
from app.services.ner.config import NERConfig
from app.services.ner.factory import build_ner_service
from app.services.ner.schemas import NERInput


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "duplicate_news_50.json"

GROUP_EXPECTATIONS: dict[str, list[str]] = {
    "duplicate_of_grp_01": ["Gebze"],
    "duplicate_of_grp_02": ["İzmit"],
    "duplicate_of_grp_03": ["Darıca"],
    "duplicate_of_grp_04": ["Gölcük"],
    "duplicate_of_grp_05": [],
    "duplicate_of_grp_06": ["Körfez"],
    "duplicate_of_grp_07": ["Başiskele"],
    "duplicate_of_grp_08": ["Kartepe"],
    "duplicate_of_grp_09": ["Derince"],
    "duplicate_of_grp_10": ["Gebze"],
    "duplicate_of_grp_11": ["Kandıra"],
    "duplicate_of_grp_12": ["Çayırova"],
    "duplicate_of_grp_13": ["İzmit"],
    "duplicate_of_grp_14": ["Kartepe"],
    "duplicate_of_grp_15": ["Darıca"],
    "duplicate_of_grp_16": ["Dilovası"],
    "duplicate_of_grp_17": ["Derince"],
    "duplicate_of_grp_18": ["Hereke"],
    "duplicate_of_grp_19": ["Başiskele"],
    "duplicate_of_grp_20": ["Gölcük"],
    "duplicate_of_grp_21": ["İzmit"],
    "duplicate_of_grp_22": ["Kandıra"],
    "duplicate_of_grp_23": ["Çayırova"],
    "duplicate_of_grp_24": ["Gebze"],
    "duplicate_of_grp_25": ["Başiskele"],
}


def _real_tests_enabled() -> bool:
    return os.getenv("RUN_REAL_TESTS", "0") == "1"


@pytest.fixture(scope="module")
def news():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def real_ner_service():
    if not _real_tests_enabled():
        pytest.skip("Gerçek testler kapalı. Çalıştırmak için RUN_REAL_TESTS=1 ayarla.")

    cfg = NERConfig(
        provider="bertturk",
        min_score=float(os.getenv("REAL_NER_MIN_SCORE", "0.50")),
        model_name=os.getenv("NER_MODEL_NAME", "savasy/bert-base-turkish-ner-cased"),
    )
    return build_ner_service(cfg)


@pytest.fixture(scope="module")
def real_geocoding_service():
    if not _real_tests_enabled():
        pytest.skip("Gerçek testler kapalı. Çalıştırmak için RUN_REAL_TESTS=1 ayarla.")

    cfg = GeocodingConfig(
        provider="nominatim",
        nominatim_url=os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org"),
        user_agent=os.getenv("NOMINATIM_USER_AGENT", "PULSE/1.0 kocaeli-news-platform"),
        timeout=int(os.getenv("GEOCODING_TIMEOUT", "10")),
        cache_ttl_seconds=int(os.getenv("GEOCODING_CACHE_TTL", "86400")),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        max_retries=int(os.getenv("GEOCODING_MAX_RETRIES", "2")),
        min_confidence=float(os.getenv("GEOCODING_MIN_CONFIDENCE", "0.3")),
        opencage_api_key=None,
    )
    return build_geocoding_service(cfg)


def test_real_ner_accuracy_on_50_news(news, real_ner_service):
    threshold = float(os.getenv("REAL_NER_ACCURACY_THRESHOLD", "0.75"))

    total = 0
    correct = 0
    for item in news:
        expected = GROUP_EXPECTATIONS[item["label"]]
        result = real_ner_service.extract_locations(
            NERInput(title=item["title"], content=item.get("content"))
        )
        if result.validated_districts == expected:
            correct += 1
        total += 1

    accuracy = correct / total if total else 0.0

    print(f"\n[REAL NER] Toplam={total} Doğru={correct} Accuracy={accuracy:.2%}")
    print(f"[REAL NER] Hedef={threshold:.0%}")

    assert accuracy >= threshold, (
        f"Gerçek NER accuracy {accuracy:.2%}, beklenen >= {threshold:.0%}"
    )


def test_live_news_location_extraction_and_geocoding(
    real_ner_service,
    real_geocoding_service,
):
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

    attempted = 0
    geocoded_success = 0
    details: list[str] = []

    for source_name, source_url, listing_scraper, detail_scraper, parser in sources:
        try:
            listing_html = listing_scraper.fetch_listing_html(source_url)
            urls = listing_scraper.extract_news_urls(listing_html)
        except Exception as exc:
            details.append(f"{source_name}: listing_fail={type(exc).__name__}")
            continue

        for url in urls[:5]:
            try:
                detail_html = detail_scraper.fetch_detail_html(url)
                detail_data = detail_scraper.extract_detail_fields(detail_html)
                record = parser.build_record(url, detail_data)
            except Exception:
                continue

            title = (record.get("title") or "").strip()
            content = (record.get("content_text") or "").strip()
            if not title or not content:
                continue

            ner_result = real_ner_service.extract_locations(
                NERInput(title=title, content=content)
            )
            if not ner_result.validated_districts:
                details.append(f"{source_name}: ner_no_district")
                break

            district = ner_result.validated_districts[0]
            attempted += 1
            geo_result = real_geocoding_service.geocode(
                GeocodingInput(address=district, district_hint=district)
            )

            if not isinstance(geo_result, GeocodingFailure):
                geocoded_success += 1
                details.append(f"{source_name}: ok={district} -> {geo_result.display_name[:45]}")
            else:
                details.append(f"{source_name}: geocode_fail={geo_result.failure_type}")
            break

    if attempted == 0:
        pytest.skip(
            "Canlı kaynaklarda bu koşuda doğrulanmış ilçe çıkarılamadı; test flakiness önlemek için skip edildi."
        )

    min_success = int(os.getenv("REAL_GEO_MIN_SUCCESS", "1"))
    print("\n[REAL LIVE NER+GEO] " + " | ".join(details))
    print(
        f"[REAL LIVE NER+GEO] denenen={attempted} basarili={geocoded_success} hedef={min_success}"
    )

    assert geocoded_success >= min_success, (
        "Canlı haber + gerçek konum testi hedefin altında: "
        f"başarılı={geocoded_success}, hedef={min_success}"
    )
