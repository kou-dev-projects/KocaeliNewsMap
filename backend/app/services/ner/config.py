from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class NERConfig:
    provider: str
    min_score: float
    model_name: str


def load_ner_config() -> NERConfig:
    return NERConfig(
        provider=os.getenv("NER_PROVIDER", "mock"),
        min_score=float(os.getenv("NER_MIN_SCORE", "0.50")),
        model_name=os.getenv(
            "NER_MODEL_NAME",
            "savasy/bert-base-turkish-ner-cased",
        ),
    )
