from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.pipelines import SourceRecordMaterializer
from app.scrapers.cagdas_kocaeli.detail import CagdasKocaeliDetailScraper
from app.scrapers.cagdas_kocaeli.listing import CagdasKocaeliListingScraper
from app.scrapers.cagdas_kocaeli.parser import CagdasKocaeliParser
from app.scrapers.ozgur_kocaeli.detail import OzgurKocaeliDetailScraper
from app.scrapers.ozgur_kocaeli.listing import OzgurKocaeliListingScraper
from app.scrapers.ozgur_kocaeli.parser import OzgurKocaeliParser
from app.scrapers.yeni_kocaeli.detail import YeniKocaeliDetailScraper
from app.scrapers.yeni_kocaeli.listing import YeniKocaeliListingScraper
from app.scrapers.yeni_kocaeli.parser import YeniKocaeliParser
from app.scripts.evaluate_location_logic import (
    VariantSpec,
    _build_variants,
    _normalize_districts,
    _predict_variant_districts,
)
from app.services.ner.districts import normalize_for_compare, recover_district_name

CURATED_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "live_location_labeled_2026_04_03.json"
)

_SOURCES = (
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
)


@dataclass(frozen=True)
class LiveSample:
    source: str
    url: str
    title: str
    content: str
    expected: list[str]
    sample_id: str | None = None
    label_method: str | None = None
    expected_location_text: str | None = None
    expected_geocode_status: str | None = None
    expected_location_resolution_method: str | None = None


@dataclass(frozen=True)
class LiveVariantResult:
    name: str
    total: int
    exact_correct: int
    primary_correct: int
    contains_expected: int
    mismatches: list[dict[str, Any]]

    @property
    def exact_accuracy(self) -> float:
        return self.exact_correct / self.total if self.total else 0.0

    @property
    def primary_accuracy(self) -> float:
        return self.primary_correct / self.total if self.total else 0.0

    @property
    def contains_accuracy(self) -> float:
        return self.contains_expected / self.total if self.total else 0.0


@dataclass(frozen=True)
class MaterializedPipelineResult:
    total: int
    district_correct: int
    geocode_status_total: int
    geocode_status_correct: int
    location_text_total: int
    location_text_correct: int
    resolution_method_total: int
    resolution_method_correct: int
    mismatches: list[dict[str, Any]]

    @property
    def district_accuracy(self) -> float:
        return self.district_correct / self.total if self.total else 0.0

    @property
    def geocode_status_accuracy(self) -> float:
        if not self.geocode_status_total:
            return 0.0
        return self.geocode_status_correct / self.geocode_status_total

    @property
    def location_text_accuracy(self) -> float:
        if not self.location_text_total:
            return 0.0
        return self.location_text_correct / self.location_text_total

    @property
    def resolution_method_accuracy(self) -> float:
        if not self.resolution_method_total:
            return 0.0
        return self.resolution_method_correct / self.resolution_method_total


def _explicit_title_districts(title: str) -> list[str]:
    tokens = title.replace("\u2019", "'").split()
    matches: list[str] = []

    for span_size in (4, 3, 2, 1):
        if len(tokens) < span_size:
            continue
        for start_index in range(len(tokens) - span_size + 1):
            span = " ".join(tokens[start_index : start_index + span_size])
            district = recover_district_name(span)
            if district:
                matches.append(district)

    return _normalize_districts(matches)


def _collect_live_samples(*, limit_per_source: int) -> list[LiveSample]:
    samples: list[LiveSample] = []

    for source_name, source_url, listing_scraper, detail_scraper, parser in _SOURCES:
        try:
            listing_html = listing_scraper.fetch_listing_html(source_url)
            urls = listing_scraper.extract_news_urls(listing_html)
        except Exception:
            continue

        collected = 0
        for url in urls[: max(limit_per_source * 3, limit_per_source)]:
            if collected >= limit_per_source:
                break

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

            expected = _explicit_title_districts(title)
            if len(expected) != 1:
                continue

            samples.append(
                LiveSample(
                    source=source_name,
                    url=url,
                    title=title,
                    content=content,
                    expected=expected,
                    label_method="weak_label_title_only",
                )
            )
            collected += 1

    return samples


def _load_curated_samples(
    fixture_path: Path,
    *,
    limit: int = 0,
) -> tuple[list[LiveSample], dict[str, Any]]:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    raw_samples = payload.get("samples", [])
    samples = [
        LiveSample(
            sample_id=item.get("id"),
            source=item["source"],
            url=item["url"],
            title=item["title"],
            content=item["content"],
            expected=_normalize_districts(item["expected"]),
            label_method=item.get("label_method", "manual_review"),
            expected_location_text=item.get("expected_location_text"),
            expected_geocode_status=item.get("expected_geocode_status"),
            expected_location_resolution_method=item.get(
                "expected_location_resolution_method"
            ),
        )
        for item in raw_samples
    ]
    if limit > 0:
        samples = samples[:limit]
    metadata = {
        "version": payload.get("version"),
        "reviewed_on": payload.get("reviewed_on"),
        "fixture_path": str(fixture_path),
    }
    return samples, metadata


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = normalize_for_compare(value)
    return normalized or None


def _evaluate_live_variant(
    variant: VariantSpec,
    samples: list[LiveSample],
) -> LiveVariantResult:
    exact_correct = 0
    primary_correct = 0
    contains_expected = 0
    mismatches: list[dict[str, Any]] = []

    for sample in samples:
        predicted = _predict_variant_districts(
            variant=variant,
            title=sample.title,
            content=sample.content,
        )
        expected_value = sample.expected[0]

        if predicted and predicted[0] == expected_value:
            primary_correct += 1
        if expected_value in predicted:
            contains_expected += 1

        if predicted == sample.expected:
            exact_correct += 1
            continue

        mismatches.append(
            {
                "sample_id": sample.sample_id,
                "source": sample.source,
                "title": sample.title,
                "url": sample.url,
                "expected": sample.expected,
                "predicted": predicted,
            }
        )

    return LiveVariantResult(
        name=variant.name,
        total=len(samples),
        exact_correct=exact_correct,
        primary_correct=primary_correct,
        contains_expected=contains_expected,
        mismatches=mismatches,
    )


def _evaluate_materialized_pipeline(
    samples: list[LiveSample],
) -> MaterializedPipelineResult:
    materializer = SourceRecordMaterializer()
    district_correct = 0
    geocode_status_total = 0
    geocode_status_correct = 0
    location_text_total = 0
    location_text_correct = 0
    resolution_method_total = 0
    resolution_method_correct = 0
    mismatches: list[dict[str, Any]] = []

    for index, sample in enumerate(samples):
        record = materializer.materialize(
            raw_document={
                "_id": sample.sample_id or f"live-sample-{index}",
                "source_id": f"source-{sample.source}",
                "canonical_url": sample.url,
                "title_raw": sample.title,
                "content_raw": sample.content,
                "text_raw": sample.content,
                "published_at_raw": "2026-04-03T10:00:00+03:00",
                "scraped_at": "2026-04-03T10:05:00+03:00",
                "language": "tr",
                "domain": sample.source,
                "resolved_url": sample.url,
            },
            source_document={
                "_id": f"source-{sample.source}",
                "display_name": sample.source,
                "base_url": f"https://{sample.source}.example",
            },
        )

        predicted_district = _normalize_districts([record.get("district_predicted")])
        district_is_correct = predicted_district == sample.expected
        if district_is_correct:
            district_correct += 1

        status_is_correct = True
        if sample.expected_geocode_status is not None:
            geocode_status_total += 1
            status_is_correct = (
                record.get("geocode_status") == sample.expected_geocode_status
            )
            if status_is_correct:
                geocode_status_correct += 1

        location_text_is_correct = True
        if sample.expected_location_text is not None:
            location_text_total += 1
            location_text_is_correct = (
                _normalize_text(record.get("location_text_extracted"))
                == _normalize_text(sample.expected_location_text)
            )
            if location_text_is_correct:
                location_text_correct += 1

        resolution_method_is_correct = True
        if sample.expected_location_resolution_method is not None:
            resolution_method_total += 1
            resolution_method_is_correct = (
                record.get("location_resolution_method")
                == sample.expected_location_resolution_method
            )
            if resolution_method_is_correct:
                resolution_method_correct += 1

        if all(
            (
                district_is_correct,
                status_is_correct,
                location_text_is_correct,
                resolution_method_is_correct,
            )
        ):
            continue

        mismatches.append(
            {
                "sample_id": sample.sample_id,
                "title": sample.title,
                "url": sample.url,
                "expected_district": sample.expected,
                "predicted_district": predicted_district,
                "expected_geocode_status": sample.expected_geocode_status,
                "predicted_geocode_status": record.get("geocode_status"),
                "expected_location_text": sample.expected_location_text,
                "predicted_location_text": record.get("location_text_extracted"),
                "expected_location_resolution_method": (
                    sample.expected_location_resolution_method
                ),
                "predicted_location_resolution_method": record.get(
                    "location_resolution_method"
                ),
            }
        )

    return MaterializedPipelineResult(
        total=len(samples),
        district_correct=district_correct,
        geocode_status_total=geocode_status_total,
        geocode_status_correct=geocode_status_correct,
        location_text_total=location_text_total,
        location_text_correct=location_text_correct,
        resolution_method_total=resolution_method_total,
        resolution_method_correct=resolution_method_correct,
        mismatches=mismatches,
    )


def _print_results(
    samples: list[LiveSample],
    results: list[LiveVariantResult],
    *,
    benchmark_label: str,
) -> None:
    print(f"\n[{benchmark_label}]")
    print(f"  labeled_samples={len(samples)}")
    header = (
        f"{'variant':<24} {'exact':>7} {'primary':>8} "
        f"{'contains':>9} {'total':>5}"
    )
    print(header)
    print("-" * len(header))
    for result in results:
        print(
            f"{result.name:<24} {result.exact_accuracy:>7.2%} "
            f"{result.primary_accuracy:>8.2%} {result.contains_accuracy:>9.2%} "
            f"{result.total:>5}"
        )
    print("")
    for result in results:
        if not result.mismatches:
            continue
        print(f"[{result.name}] ilk 5 mismatch")
        for mismatch in result.mismatches[:5]:
            print(
                f"  - {mismatch['source']}: expected={mismatch['expected']} "
                f"predicted={mismatch['predicted']} | {mismatch['title']}"
            )
            print(f"    {mismatch['url']}")
        print("")


def _print_materialized_result(result: MaterializedPipelineResult) -> None:
    print("[Materialized Pipeline]")
    print(
        "  district_accuracy="
        f"{result.district_accuracy:.2%} ({result.district_correct}/{result.total})"
    )
    if result.geocode_status_total:
        print(
            "  geocode_status_accuracy="
            f"{result.geocode_status_accuracy:.2%} "
            f"({result.geocode_status_correct}/{result.geocode_status_total})"
        )
    if result.location_text_total:
        print(
            "  location_text_accuracy="
            f"{result.location_text_accuracy:.2%} "
            f"({result.location_text_correct}/{result.location_text_total})"
        )
    if result.resolution_method_total:
        print(
            "  resolution_method_accuracy="
            f"{result.resolution_method_accuracy:.2%} "
            f"({result.resolution_method_correct}/{result.resolution_method_total})"
        )
    if result.mismatches:
        print("  ilk 5 mismatch")
        for mismatch in result.mismatches[:5]:
            print(
                f"  - district expected={mismatch['expected_district']} "
                f"predicted={mismatch['predicted_district']} | {mismatch['title']}"
            )
            if mismatch["expected_geocode_status"] is not None:
                print(
                    "    geocode_status "
                    f"expected={mismatch['expected_geocode_status']} "
                    f"predicted={mismatch['predicted_geocode_status']}"
                )
            if mismatch["expected_location_text"] is not None:
                print(
                    "    location_text "
                    f"expected={mismatch['expected_location_text']} "
                    f"predicted={mismatch['predicted_location_text']}"
                )
            if mismatch["expected_location_resolution_method"] is not None:
                print(
                    "    resolution_method "
                    f"expected={mismatch['expected_location_resolution_method']} "
                    f"predicted={mismatch['predicted_location_resolution_method']}"
                )
            print(f"    {mismatch['url']}")
    print("")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate location logic on manually labeled or weak-label live samples."
    )
    parser.add_argument(
        "--mode",
        choices=("curated", "weak-label"),
        default="curated",
        help="Curated fixture ile veya basliktan turetilen weak-label set ile calistir.",
    )
    parser.add_argument(
        "--fixture",
        default=str(CURATED_FIXTURE),
        help="Curated benchmark fixture yolu.",
    )
    parser.add_argument(
        "--limit-per-source",
        type=int,
        default=3,
        help="Weak-label modunda her kaynak icin en fazla kac haber alinacak.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Curated benchmark icin en fazla kac ornek calistirilacak.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Sonucu JSON olarak da yazdir.",
    )
    args = parser.parse_args()

    fixture_metadata: dict[str, Any] = {}
    if args.mode == "curated":
        samples, fixture_metadata = _load_curated_samples(
            Path(args.fixture),
            limit=max(args.limit, 0),
        )
        benchmark_label = "Live Labeled Benchmark"
    else:
        samples = _collect_live_samples(limit_per_source=max(args.limit_per_source, 1))
        benchmark_label = "Live Weak-Label Benchmark"

    variants = _build_variants(include_mock=False)
    results = [_evaluate_live_variant(variant, samples) for variant in variants]
    materialized_pipeline_result = (
        _evaluate_materialized_pipeline(samples)
        if args.mode == "curated"
        else None
    )

    _print_results(samples, results, benchmark_label=benchmark_label)
    if materialized_pipeline_result is not None:
        _print_materialized_result(materialized_pipeline_result)

    if args.json:
        payload = {
            "mode": args.mode,
            "benchmark_label": benchmark_label,
            "fixture_metadata": fixture_metadata,
            "samples": [asdict(sample) for sample in samples],
            "materialized_pipeline": (
                {
                    **asdict(materialized_pipeline_result),
                    "district_accuracy": materialized_pipeline_result.district_accuracy,
                    "geocode_status_accuracy": (
                        materialized_pipeline_result.geocode_status_accuracy
                    ),
                    "location_text_accuracy": (
                        materialized_pipeline_result.location_text_accuracy
                    ),
                    "resolution_method_accuracy": (
                        materialized_pipeline_result.resolution_method_accuracy
                    ),
                }
                if materialized_pipeline_result is not None
                else None
            ),
            "results": [
                {
                    **asdict(result),
                    "exact_accuracy": result.exact_accuracy,
                    "primary_accuracy": result.primary_accuracy,
                    "contains_accuracy": result.contains_accuracy,
                }
                for result in results
            ],
        }
        print("\n[JSON]")
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
