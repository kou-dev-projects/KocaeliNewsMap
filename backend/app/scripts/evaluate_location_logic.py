from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.evaluation.location_benchmarks import (
    DISTRICT_GROUP_EXPECTATIONS,
    LOGICAL_BENCHMARK_CASES,
)
from app.services.classifier.schemas import ClassificationResult
from app.services.logical_location import build_logical_location_candidates
from app.services.ner.config import NERConfig, load_ner_config
from app.services.ner.districts import normalize_for_compare
from app.services.ner.factory import build_ner_service
from app.services.ner.providers.bertturk import BERTTurkNERProvider
from app.services.ner.schemas import LocationCandidate, NERInput, NERResult
from app.services.ner.service import NERService

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "duplicate_news_50.json"


class EmptyNERProvider:
    name = "empty-ner"

    def extract_entities(self, text: str) -> list[Any]:
        return []


@dataclass(frozen=True)
class VariantSpec:
    name: str
    service: NERService
    use_gazetteer: bool
    use_heuristic: bool
    use_provider: bool


@dataclass(frozen=True)
class DistrictBenchmarkResult:
    name: str
    total: int
    correct: int
    false_negative: int
    false_positive: int
    wrong_district: int
    mismatches: list[dict[str, Any]]

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


@dataclass(frozen=True)
class LogicalBenchmarkResult:
    total: int
    correct: int
    mismatches: list[dict[str, Any]]

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def _load_news() -> list[dict[str, Any]]:
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_districts(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_for_compare(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _build_bertturk_service() -> NERService:
    cfg = load_ner_config()
    model_name = cfg.model_name or "savasy/bert-base-turkish-ner-cased"
    return NERService(
        provider=BERTTurkNERProvider(model_name=model_name),
        min_score=cfg.min_score,
    )


def _evaluate_variant(
    variant: VariantSpec,
    news: list[dict[str, Any]],
) -> DistrictBenchmarkResult:
    total = 0
    correct = 0
    false_negative = 0
    false_positive = 0
    wrong_district = 0
    mismatches: list[dict[str, Any]] = []

    for item in news:
        expected = _normalize_districts(
            DISTRICT_GROUP_EXPECTATIONS.get(item["label"], [])
        )
        predicted = _predict_variant_districts(
            variant=variant,
            title=item["title"],
            content=item.get("content") or "",
        )

        total += 1
        if predicted == expected:
            correct += 1
            continue

        if expected and not predicted:
            false_negative += 1
        elif not expected and predicted:
            false_positive += 1
        else:
            wrong_district += 1

        mismatches.append(
            {
                "id": item["id"],
                "title": item["title"],
                "expected": expected,
                "predicted": predicted,
            }
        )

    return DistrictBenchmarkResult(
        name=variant.name,
        total=total,
        correct=correct,
        false_negative=false_negative,
        false_positive=false_positive,
        wrong_district=wrong_district,
        mismatches=mismatches,
    )


def _predict_variant_districts(
    *,
    variant: VariantSpec,
    title: str,
    content: str,
) -> list[str]:
    service = variant.service
    input_data = NERInput(title=title, content=content)
    text = input_data.build_text_payload()

    seeds: list[LocationCandidate] = []
    if variant.use_gazetteer:
        seeds.extend(service._gazetteer_pass(text))
    if variant.use_heuristic:
        seeds.extend(service._heuristic_location_pass(text))

    entities: list[Any] = []
    if variant.use_provider:
        entities = service._provider.extract_entities(text)

    _, validated = service._merge_and_validate(seeds, entities)
    title_district_hints = (
        service._extract_title_district_hints(title) if variant.use_gazetteer else []
    )
    validated = service._finalize_validated_districts(
        validated_districts=validated,
        title_district_hints=title_district_hints,
    )
    return _normalize_districts(validated)


def _evaluate_logical_benchmarks() -> LogicalBenchmarkResult:
    mismatches: list[dict[str, Any]] = []
    correct = 0

    for case in LOGICAL_BENCHMARK_CASES:
        ner_result = NERResult(
            raw_entities=[],
            location_candidates=[
                LocationCandidate(
                    original_text=spec.original_text,
                    normalized_text=normalize_for_compare(spec.original_text),
                    score=spec.score,
                    is_kocaeli_district=spec.is_kocaeli_district,
                    district=spec.district,
                    neighborhood=spec.neighborhood,
                    feature_type=spec.feature_type,
                )
                for spec in case.seed_candidates
            ],
            validated_districts=case.validated_districts,
            provider="benchmark",
        )

        candidates = build_logical_location_candidates(
            title=case.title,
            summary=case.summary,
            body=case.body,
            classification=ClassificationResult(
                category=case.category,
                confidence=1.0,
                method="benchmark",
            ),
            ner_result=ner_result,
            fallback_district=case.fallback_district,
        )

        actual_strategy = candidates[0].strategy if candidates else None
        actual_address = candidates[0].address if candidates else None

        if (
            actual_strategy == case.expected_strategy
            and actual_address == case.expected_address
        ):
            correct += 1
            continue

        mismatches.append(
            {
                "case": case.name,
                "expected_strategy": case.expected_strategy,
                "actual_strategy": actual_strategy,
                "expected_address": case.expected_address,
                "actual_address": actual_address,
            }
        )

    return LogicalBenchmarkResult(
        total=len(LOGICAL_BENCHMARK_CASES),
        correct=correct,
        mismatches=mismatches,
    )


def _build_variants(include_mock: bool) -> list[VariantSpec]:
    empty_service = NERService(provider=EmptyNERProvider(), min_score=0.5)
    bertturk_service = _build_bertturk_service()

    variants = [
        VariantSpec(
            name="gazetteer_only",
            service=empty_service,
            use_gazetteer=True,
            use_heuristic=False,
            use_provider=False,
        ),
        VariantSpec(
            name="heuristic_only",
            service=empty_service,
            use_gazetteer=False,
            use_heuristic=True,
            use_provider=False,
        ),
        VariantSpec(
            name="seed_rules_combined",
            service=empty_service,
            use_gazetteer=True,
            use_heuristic=True,
            use_provider=False,
        ),
        VariantSpec(
            name="provider_only_bertturk",
            service=bertturk_service,
            use_gazetteer=False,
            use_heuristic=False,
            use_provider=True,
        ),
        VariantSpec(
            name="full_pipeline_bertturk",
            service=bertturk_service,
            use_gazetteer=True,
            use_heuristic=True,
            use_provider=True,
        ),
    ]

    if include_mock:
        mock_service = build_ner_service(
            NERConfig(provider="mock", min_score=0.5, model_name="")
        )
        variants.append(
            VariantSpec(
                name="full_pipeline_mock",
                service=mock_service,
                use_gazetteer=True,
                use_heuristic=True,
                use_provider=True,
            )
        )

    return variants


def _print_district_results(results: list[DistrictBenchmarkResult]) -> None:
    print("\n[District Benchmark: duplicate_news_50]")
    header = (
        f"{'variant':<24} {'correct':>7} {'total':>5} {'acc':>8} "
        f"{'fn':>5} {'fp':>5} {'wrong':>7}"
    )
    print(header)
    print("-" * len(header))
    for result in results:
        print(
            f"{result.name:<24} {result.correct:>7} {result.total:>5} "
            f"{result.accuracy:>7.2%} {result.false_negative:>5} "
            f"{result.false_positive:>5} {result.wrong_district:>7}"
        )
    print("")
    for result in results:
        if not result.mismatches:
            continue
        print(f"[{result.name}] ilk 5 mismatch")
        for mismatch in result.mismatches[:5]:
            print(
                f"  - {mismatch['id']}: expected={mismatch['expected']} "
                f"predicted={mismatch['predicted']} | {mismatch['title']}"
            )
        print("")


def _print_logical_result(result: LogicalBenchmarkResult) -> None:
    print("[Logical Benchmark]")
    print(
        f"  toplam={result.total} dogru={result.correct} "
        f"accuracy={result.accuracy:.2%}"
    )
    if result.mismatches:
        print("  mismatchler:")
        for mismatch in result.mismatches:
            print(
                f"  - {mismatch['case']}: "
                f"expected=({mismatch['expected_strategy']}, {mismatch['expected_address']}) "
                f"actual=({mismatch['actual_strategy']}, {mismatch['actual_address']})"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Location logic benchmark runner"
    )
    parser.add_argument(
        "--no-mock",
        action="store_true",
        help="Mock provider varyantini calistirma",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Sonucu JSON olarak da yazdir",
    )
    args = parser.parse_args()

    news = _load_news()
    district_results = [
        _evaluate_variant(variant, news)
        for variant in _build_variants(include_mock=not args.no_mock)
    ]
    logical_result = _evaluate_logical_benchmarks()

    _print_district_results(district_results)
    _print_logical_result(logical_result)

    if args.json:
        payload = {
            "district_results": [
                {
                    **asdict(result),
                    "accuracy": result.accuracy,
                }
                for result in district_results
            ],
            "logical_result": {
                **asdict(logical_result),
                "accuracy": logical_result.accuracy,
            },
        }
        print("\n[JSON]")
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
