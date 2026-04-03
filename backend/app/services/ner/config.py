from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NERConfig:
    provider: str
    min_score: float
    model_name: str
    gliner_threshold: float = 0.50


def load_ner_config() -> NERConfig:
    from app.settings import settings

    provider = settings.ner_provider

    if provider == "gliner":
        model_name = settings.gliner_model_name
    elif provider == "bertturk":
        model_name = settings.bertturk_model_name
    else:
        model_name = ""

    return NERConfig(
        provider=provider,
        min_score=settings.ner_min_score,
        model_name=model_name,
        gliner_threshold=settings.gliner_threshold,
    )
