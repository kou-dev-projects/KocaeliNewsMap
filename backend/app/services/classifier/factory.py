from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from .keyword_classifier import KeywordClassifier
from .resolver import ConflictResolver
from .semantic_classifier import SemanticClassifier
from .service import ClassifierService

if TYPE_CHECKING:
    from app.services.embedding import EmbeddingService


def build_classifier_service(
    embedding_service: Optional["EmbeddingService"] = None,
) -> ClassifierService:
   
    return ClassifierService(
        keyword_classifier=KeywordClassifier(),
        semantic_classifier=SemanticClassifier(embedding_service),
        resolver=ConflictResolver(),
    )