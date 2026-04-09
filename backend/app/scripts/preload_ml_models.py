from __future__ import annotations

import argparse
import logging
import time

from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.local_factory import (
    build_local_text_provider,
)
from app.services.ner.config import NERConfig
from app.services.ner.local_factory import build_local_ner_service
from app.services.ner.schemas import NERInput


logger = logging.getLogger(__name__)


def _build_embedding_config(
    *,
    text_provider: str,
) -> EmbeddingConfig:
    return EmbeddingConfig(
        text_provider=text_provider,
        text_dimension=1024,
        duplicate_threshold=0.90,
        text_score_weight=1.00,
        cost_log_path="logs/embedding_cost.jsonl",
    )


def preload_ner(
    *,
    provider: str,
    model_name: str,
    min_score: float,
    gliner_threshold: float,
) -> None:
    if provider == "mock":
        return

    logger.info(
        "preload_ml_models.start",
        extra={"provider_type": "ner", "provider": provider},
    )
    started_at = time.perf_counter()
    service = build_local_ner_service(
        NERConfig(
            provider=provider,
            min_score=min_score,
            model_name=model_name,
            gliner_threshold=gliner_threshold,
        ),
        allow_fallback=False,
    )
    service.extract_locations(
        NERInput(
            title="Izmit'te trafik kazasi nedeniyle yol kapandi",
            content="Kocaeli genelinde trafik akisi izleniyor.",
        )
    )
    logger.info(
        "preload_ml_models.ready",
        extra={
            "provider_type": "ner",
            "provider": provider,
            "elapsed_seconds": round(time.perf_counter() - started_at, 2),
        },
    )


def preload_text(*, provider: str) -> None:
    if provider == "mock":
        return

    logger.info(
        "preload_ml_models.start",
        extra={"provider_type": "embedding_text", "provider": provider},
    )
    started_at = time.perf_counter()
    embedding_provider = build_local_text_provider(
        _build_embedding_config(text_provider=provider),
        allow_fallback=False,
    )
    get_model = getattr(embedding_provider, "_get_model", None)
    if callable(get_model):
        get_model()
    else:
        embedding_provider.embed_text("Kocaeli'de guncel trafik ve asayis ozeti")
    logger.info(
        "preload_ml_models.ready",
        extra={
            "provider_type": "embedding_text",
            "provider": provider,
            "elapsed_seconds": round(time.perf_counter() - started_at, 2),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ner-provider", default="mock")
    parser.add_argument("--ner-model", default="")
    parser.add_argument("--ner-min-score", type=float, default=0.50)
    parser.add_argument("--gliner-threshold", type=float, default=0.50)
    parser.add_argument("--text-provider", default="mock")
    args = parser.parse_args()

    preload_ner(
        provider=args.ner_provider,
        model_name=args.ner_model,
        min_score=args.ner_min_score,
        gliner_threshold=args.gliner_threshold,
    )
    preload_text(provider=args.text_provider)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
