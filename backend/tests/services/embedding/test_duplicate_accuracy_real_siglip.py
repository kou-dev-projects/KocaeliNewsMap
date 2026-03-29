from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.factory import build_embedding_service
from app.services.embedding.schemas import EmbeddingInput

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "real_multimodal_news_6.json"


def _siglip_tests_enabled() -> bool:
    return os.getenv("RUN_REAL_SIGLIP_TESTS", "0") == "1"


@pytest.fixture(scope="module")
def news():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def multimodal_service():
    if not _siglip_tests_enabled():
        pytest.skip("SigLIP real test kapali. Calistirmak icin RUN_REAL_SIGLIP_TESTS=1 ayarla.")

    cfg = EmbeddingConfig(
        text_provider="bge-m3",
        image_provider="siglip2",
        text_dimension=1024,
        image_dimension=768,
        duplicate_threshold=float(os.getenv("REAL_SIGLIP_DUP_THRESHOLD", "0.92")),
        text_score_weight=float(os.getenv("REAL_SIGLIP_TEXT_WEIGHT", "0.70")),
        image_score_weight=float(os.getenv("REAL_SIGLIP_IMAGE_WEIGHT", "0.30")),
        cost_log_path=os.getenv("EMBEDDING_COST_LOG", "logs/embedding_cost.jsonl"),
    )
    return build_embedding_service(cfg)


def test_real_siglip_multimodal_duplicate_decisions(news, multimodal_service):
    embeddings: dict[str, tuple] = {}

    for item in news:
        inp = EmbeddingInput(
            title=item["title"],
            source=item["source"],
            content=item.get("content"),
            image_url=item.get("image_url"),
        )
        text_emb, image_emb = multimodal_service.embed(inp)
        embeddings[item["id"]] = (text_emb, image_emb)

    image_ok = sum(1 for _id, (_t, img) in embeddings.items() if img is not None)
    if image_ok < 4:
        pytest.skip(
            f"Yeterli gorsel embedding olusmadi (image_ok={image_ok}/6). Ag ya da remote gorsel sorunu olabilir."
        )

    dup_pairs = [("m001", "m002"), ("m004", "m005")]
    non_dup_pairs = [("m001", "m003"), ("m004", "m006")]

    for left, right in dup_pairs:
        left_text, left_img = embeddings[left]
        right_text, right_img = embeddings[right]

        result = multimodal_service.decide_duplicate(
            left_text,
            left_img,
            [
                {
                    "id": right,
                    "text_vector": right_text.vector,
                    "image_vector": right_img.vector if right_img else None,
                    "kaynak_listesi": ["source-x.com"],
                }
            ],
            "source-y.com",
        )

        assert result.is_duplicate is True
        assert result.debug is not None and result.debug.get("image_used") is True

    for left, right in non_dup_pairs:
        left_text, left_img = embeddings[left]
        right_text, right_img = embeddings[right]

        result = multimodal_service.decide_duplicate(
            left_text,
            left_img,
            [
                {
                    "id": right,
                    "text_vector": right_text.vector,
                    "image_vector": right_img.vector if right_img else None,
                    "kaynak_listesi": ["source-x.com"],
                }
            ],
            "source-y.com",
        )

        assert result.is_duplicate is False
