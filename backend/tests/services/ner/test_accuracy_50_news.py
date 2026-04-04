from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.ner import build_ner_service
from app.services.ner.config import NERConfig
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


@pytest.fixture(scope="module")
def news():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def svc():
    cfg = NERConfig(
        provider="mock",
        min_score=0.50,
        model_name="",
    )
    return build_ner_service(cfg)


def test_fixture_has_50_news(news):
    assert len(news) >= 50, f"En az 50 haber gerekli, şu an {len(news)}"


def test_location_extraction_accuracy_on_50_news(news, svc):
    total = correct = 0
    false_negative = 0
    false_positive = 0
    wrong_district = 0
    mismatches: list[tuple[str, list[str], list[str], str]] = []

    for item in news:
        expected = GROUP_EXPECTATIONS[item["label"]]
        result = svc.extract_locations(
            NERInput(
                title=item["title"],
                content=item.get("content"),
            )
        )
        predicted = result.validated_districts

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

        mismatches.append((item["id"], expected, predicted, item["title"]))

    accuracy = correct / total

    print(f"\n{'=' * 60}")
    print("[S1 NER Location Accuracy Report]")
    print(f"  Toplam: {total} | Doğru: {correct} | Yanlış: {total - correct}")
    print(f"  False Negative: {false_negative}")
    print(f"  False Positive: {false_positive}")
    print(f"  Wrong District: {wrong_district}")
    print(f"  Accuracy: {accuracy:.2%}")
    print("  Hedef: 95%")
    if mismatches:
        print("  İlk 10 mismatch:")
        for news_id, expected, predicted, title in mismatches[:10]:
            print(f"    - {news_id}: expected={expected} predicted={predicted} | {title}")
    print(f"{'=' * 60}")

    assert accuracy >= 0.95
