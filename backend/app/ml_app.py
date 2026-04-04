from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.embedding.config import EmbeddingConfig, load_embedding_config
from app.services.embedding.local_factory import (
    build_local_image_provider,
    build_local_text_provider,
)
from app.services.ner.config import NERConfig, load_ner_config
from app.services.ner.local_factory import build_local_ner_service
from app.services.ner.schemas import NERInput


logger = logging.getLogger(__name__)


def _env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() == "true"


class NERExtractLocationsRequest(BaseModel):
    provider: str
    model_name: str = ""
    min_score: float = 0.50
    gliner_threshold: float = 0.50
    title: str
    summary: str | None = None
    content: str | None = None


class TextEmbeddingRequest(BaseModel):
    provider: str
    text: str
    dimension: int


class ImageEmbeddingRequest(BaseModel):
    provider: str
    image_url: str
    dimension: int


def _warm_ner_provider(config: NERConfig) -> None:
    if config.provider == "mock":
        return

    started_at = time.perf_counter()
    service = build_local_ner_service(config, allow_fallback=False)
    service.extract_locations(
        NERInput(
            title="Izmit'te trafik kazasi nedeniyle yol kapandi",
            content="Kocaeli genelinde trafik akisi izleniyor.",
        )
    )
    logger.info(
        "ml_app.provider_ready",
        extra={
            "provider_type": "ner",
            "provider": config.provider,
            "elapsed_seconds": round(time.perf_counter() - started_at, 2),
        },
    )


def _warm_text_provider(config: EmbeddingConfig) -> None:
    if config.text_provider == "mock":
        return

    started_at = time.perf_counter()
    provider = build_local_text_provider(config, allow_fallback=False)
    provider.embed_text("Kocaeli'de guncel trafik ve asayis ozeti")
    logger.info(
        "ml_app.provider_ready",
        extra={
            "provider_type": "embedding_text",
            "provider": config.text_provider,
            "elapsed_seconds": round(time.perf_counter() - started_at, 2),
        },
    )


def _warm_image_provider(config: EmbeddingConfig) -> None:
    if config.image_provider == "mock":
        return

    started_at = time.perf_counter()
    provider = build_local_image_provider(config, allow_fallback=False)
    get_model = getattr(provider, "_get_model", None)
    if callable(get_model):
        get_model()
    logger.info(
        "ml_app.provider_ready",
        extra={
            "provider_type": "embedding_image",
            "provider": config.image_provider,
            "elapsed_seconds": round(time.perf_counter() - started_at, 2),
        },
    )


def _warm_configured_providers() -> None:
    ner_config = load_ner_config()
    embedding_config = load_embedding_config()

    if _env_flag("ML_SERVICE_WARM_NER_PROVIDER"):
        _warm_ner_provider(ner_config)
    if _env_flag("ML_SERVICE_WARM_TEXT_PROVIDER"):
        _warm_text_provider(embedding_config)
    if _env_flag("ML_SERVICE_WARM_IMAGE_PROVIDER"):
        _warm_image_provider(embedding_config)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _warm_configured_providers()
    yield


app = FastAPI(
    title="PULSE ML Service",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {"message": "ML service is running"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/ner/extract-locations")
def ner_extract_locations(request: NERExtractLocationsRequest):
    try:
        service = build_local_ner_service(
            NERConfig(
                provider=request.provider,
                min_score=request.min_score,
                model_name=request.model_name,
                gliner_threshold=request.gliner_threshold,
            ),
            allow_fallback=False,
        )
        result = service.extract_locations(
            NERInput(
                title=request.title,
                summary=request.summary,
                content=request.content,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return asdict(result)


@app.post("/embedding/text")
def embedding_text(request: TextEmbeddingRequest):
    try:
        provider = build_local_text_provider(
            EmbeddingConfig(
                text_provider=request.provider,
                image_provider="mock",
                text_dimension=request.dimension,
                image_dimension=768,
                duplicate_threshold=0.90,
                text_score_weight=0.85,
                image_score_weight=0.15,
                cost_log_path="logs/embedding_cost.jsonl",
            ),
            allow_fallback=False,
        )
        vector = provider.embed_text(request.text)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "provider": provider.name,
        "dimension": int(len(vector)),
        "vector": vector.tolist(),
    }


@app.post("/embedding/image")
def embedding_image(request: ImageEmbeddingRequest):
    try:
        provider = build_local_image_provider(
            EmbeddingConfig(
                text_provider="mock",
                image_provider=request.provider,
                text_dimension=1024,
                image_dimension=request.dimension,
                duplicate_threshold=0.90,
                text_score_weight=0.85,
                image_score_weight=0.15,
                cost_log_path="logs/embedding_cost.jsonl",
            ),
            allow_fallback=False,
        )
        vector = provider.embed_image(request.image_url)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "provider": provider.name,
        "dimension": int(len(vector)) if vector is not None else request.dimension,
        "vector": vector.tolist() if vector is not None else None,
    }
