from __future__ import annotations
import json
import pytest
from pathlib import Path

from app.services.embedding import build_embedding_service
from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.schemas import EmbeddingInput

FIXTURE = Path(__file__).parent.parent.parent / "fixtures" / "duplicate_news_50.json"

@pytest.fixture(scope="module")
def news():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def svc():
    cfg = EmbeddingConfig(
        text_provider="mock",
        text_dimension=1024,
        duplicate_threshold=0.90,
        text_score_weight=1.00,
        cost_log_path="/tmp/accuracy_test_cost.jsonl",
    )
    return build_embedding_service(cfg)


def test_fixture_has_minimum_count(news):
    assert len(news) >= 50, f"En az 50 haber gerekli, şu an {len(news)}"


def test_duplicate_accuracy(news, svc):
   
    # 1) Tüm embedding'leri üret
    embeddings: dict[str, object] = {}
    for item in news:
        inp = EmbeddingInput(
            title=item["title"],
            source=item["source"],
            content=item.get("content"),
        )
        text_emb = svc.embed(inp)
        embeddings[item["id"]] = text_emb

    # 2) Her haber için karar ver
    total = correct = false_positive = false_negative = 0

    for item in news:
        text_emb = embeddings[item["id"]]
        is_actual_dup = item["label"].startswith("duplicate_of_")

        candidates = [
            {
                "id": other["id"],
                "text_vector": embeddings[other["id"]].vector,
                "kaynak_listesi": [other["source"]],
            }
            for other in news if other["id"] != item["id"]
        ]

        result = svc.decide_duplicate(text_emb, candidates, item["source"])

        total += 1
        if result.is_duplicate == is_actual_dup:
            correct += 1
        elif result.is_duplicate and not is_actual_dup:
            false_positive += 1
        else:
            false_negative += 1

    accuracy = correct / total

    print(f"\n{'='*50}")
    print("[S1-004 Duplicate Accuracy Report]")
    print(f"  Toplam: {total} | Doğru: {correct} | Yanlış: {total - correct}")
    print(f"  False Positive: {false_positive} | False Negative: {false_negative}")
    print(f"  Accuracy: {accuracy:.2%}")
    print("  Threshold: 0.90 | Hedef: 95%")
    print(f"  Sonuç: {'✓ GEÇTİ' if accuracy >= 0.95 else '✗ KALDI'}")
    print(f"{'='*50}")

    assert accuracy >= 0.95, (
        f"Duplicate accuracy {accuracy:.2%} — hedef %95. "
        f"FP={false_positive} FN={false_negative}"
    )