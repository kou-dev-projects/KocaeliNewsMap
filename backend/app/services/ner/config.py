from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class NERConfig:
    provider: str
    min_score: float
    model_name: str
    gliner_threshold: float = 0.50


def load_ner_config() -> NERConfig:
    provider = os.getenv("NER_PROVIDER", "mock")

    if provider == "gliner":
        model_name = os.getenv("GLINER_MODEL_NAME", "urchade/gliner_multi-v2.1")
    elif provider == "bertturk":
        model_name = os.getenv("BERTTURK_MODEL_NAME", "savasy/bert-base-turkish-ner-cased")
    else:
        model_name = ""

    return NERConfig(
        provider=provider,
        min_score=float(os.getenv("NER_MIN_SCORE", "0.50")),
        model_name=model_name,
        gliner_threshold=float(os.getenv("GLINER_THRESHOLD", "0.50")),
    )
