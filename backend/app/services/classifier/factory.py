from __future__ import annotations
from typing import TYPE_CHECKING
from .config import load_classifier_config

from .keyword_classifier import KeywordClassifier
from .resolver import ConflictResolver
from .semantic_classifier import SemanticClassifier
from .service import ClassifierService

if TYPE_CHECKING:
    pass


def build_classifier_service(embedding_service=None):
    cfg = load_classifier_config()
    return ClassifierService(
        keyword_classifier=KeywordClassifier(),
        semantic_classifier=SemanticClassifier(
            embedding_service=embedding_service,
            threshold=cfg.semantic_confidence_threshold,
        ),
        resolver=ConflictResolver(),
        semantic_enabled=cfg.semantic_enabled,
        keyword_only_mode=cfg.keyword_only_mode,
    )