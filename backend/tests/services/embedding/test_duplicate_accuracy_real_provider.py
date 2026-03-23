from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.factory import build_embedding_service
from app.services.embedding.schemas import EmbeddingInput

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "duplicate_news_50.json"


def _real_tests_enabled() -> bool:
    return os.getenv("RUN_REAL_TESTS", "0") == "1"


@pytest.fixture(scope="module")
def news():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def real_embedding_service():
    if not _real_tests_enabled():
        pytest.skip("Gerçek testler kapalı. Çalıştırmak için RUN_REAL_TESTS=1 ayarla.")

    cfg = EmbeddingConfig(
        text_provider="bge-m3",
        image_provider="mock",
        text_dimension=1024,
        image_dimension=768,
        duplicate_threshold=float(os.getenv("DUPLICATE_THRESHOLD", "0.90")),
        text_score_weight=float(os.getenv("DUPLICATE_TEXT_WEIGHT", "0.85")),
        image_score_weight=float(os.getenv("DUPLICATE_IMAGE_WEIGHT", "0.15")),
        cost_log_path=os.getenv("EMBEDDING_COST_LOG", "logs/embedding_cost.jsonl"),
    )
    return build_embedding_service(cfg)


def test_duplicate_accuracy_with_real_text_embeddings(news, real_embedding_service):
    threshold = float(os.getenv("REAL_DUPLICATE_ACCURACY_THRESHOLD", "0.90"))

    embeddings: dict[str, tuple] = {}
    for item in news:
        inp = EmbeddingInput(
            title=item["title"],
            source=item["source"],
            content=item.get("content"),
            image_url=None,
        )
        text_emb, image_emb = real_embedding_service.embed(inp)
        embeddings[item["id"]] = (text_emb, image_emb)

    total = 0
    correct = 0
    false_positive = 0
    false_negative = 0

    for item in news:
        text_emb, image_emb = embeddings[item["id"]]
        is_actual_dup = item["label"].startswith("duplicate_of_")

        candidates = [
            {
                "id": other["id"],
                "text_vector": embeddings[other["id"]][0].vector,
                "image_vector": None,
                "kaynak_listesi": [other["source"]],
            }
            for other in news
            if other["id"] != item["id"]
        ]

        result = real_embedding_service.decide_duplicate(
            text_emb,
            image_emb,
            candidates,
            item["source"],
        )

        total += 1
        if result.is_duplicate == is_actual_dup:
            correct += 1
        elif result.is_duplicate:
            false_positive += 1
        else:
            false_negative += 1

    accuracy = correct / total if total else 0.0

    print(
        f"\n[REAL EMBEDDING] Toplam={total} Doğru={correct} "
        f"FP={false_positive} FN={false_negative} Accuracy={accuracy:.2%}"
    )
    print(f"[REAL EMBEDDING] Hedef={threshold:.0%}")

    assert accuracy >= threshold, (
        f"Gerçek embedding duplicate accuracy {accuracy:.2%}, beklenen >= {threshold:.0%}"
    )