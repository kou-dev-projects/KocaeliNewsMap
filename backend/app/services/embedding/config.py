from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingConfig:
    # Provider seçimi
    text_provider: str        # "mock" | "bge-m3"
    image_provider: str       # "mock" | "siglip2"

    # Boyutlar — provider'a göre sabit
    text_dimension: int       # BGE-M3: 1024
    image_dimension: int      # SigLIP2: 768

    # Duplicate karar parametreleri — 50 haber testinden sonra ayarlanır
    duplicate_threshold: float   # default 0.90
    text_score_weight: float     # default 0.85
    image_score_weight: float    # default 0.15

    # Log
    cost_log_path: str


def load_embedding_config() -> EmbeddingConfig:
    return EmbeddingConfig(
        text_provider=os.getenv("EMBEDDING_TEXT_PROVIDER", "mock"),
        image_provider=os.getenv("EMBEDDING_IMAGE_PROVIDER", "mock"),
        text_dimension=int(os.getenv("EMBEDDING_TEXT_DIM", "1024")),
        image_dimension=int(os.getenv("EMBEDDING_IMAGE_DIM", "768")),
        duplicate_threshold=float(os.getenv("DUPLICATE_THRESHOLD", "0.90")),
        text_score_weight=float(os.getenv("DUPLICATE_TEXT_WEIGHT", "0.85")),
        image_score_weight=float(os.getenv("DUPLICATE_IMAGE_WEIGHT", "0.15")),
        cost_log_path=os.getenv("EMBEDDING_COST_LOG", "logs/embedding_cost.jsonl"),
    )