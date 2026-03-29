from __future__ import annotations
from dataclasses import dataclass

from app.settings import settings


@dataclass(frozen=True)
class ClassifierConfig:
  
    semantic_enabled: bool
    semantic_confidence_threshold: float
    keyword_only_mode: bool


def load_classifier_config() -> ClassifierConfig:
    return ClassifierConfig(
    semantic_enabled=settings.classifier_semantic_enabled,
    semantic_confidence_threshold=settings.classifier_semantic_threshold,
    keyword_only_mode=settings.classifier_keyword_only,
    )