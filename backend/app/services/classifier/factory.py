from __future__ import annotations
from typing import TYPE_CHECKING
from .config import load_classifier_config

from app.services.embedding.factory import build_embedding_service

from .keyword_classifier import KeywordClassifier
from .resolver import ConflictResolver
from .semantic_classifier import SemanticClassifier
from .service import ClassifierService

if TYPE_CHECKING:
    pass


def build_classifier_service(embedding_service=None):
    cfg = load_classifier_config()
    semantic_enabled = cfg.semantic_enabled and not cfg.keyword_only_mode

    if semantic_enabled and embedding_service is None:
        try:
            embedding_service = build_embedding_service()
        except Exception:
            semantic_enabled = False

    return ClassifierService(
        keyword_classifier=KeywordClassifier(),
        semantic_classifier=SemanticClassifier(
            embedding_service=embedding_service,
            threshold=cfg.semantic_confidence_threshold,
            margin_threshold=cfg.semantic_margin_threshold,
        ),
        resolver=ConflictResolver(),
        semantic_enabled=semantic_enabled,
        keyword_only_mode=cfg.keyword_only_mode,
    )
