from __future__ import annotations
import logging

from .keyword_classifier import KeywordClassifier
from .resolver import ConflictResolver
from .schemas import ClassificationInput, ClassificationResult, NewsCategory
from .semantic_classifier import SemanticClassifier

logger = logging.getLogger(__name__)


class ClassifierService:

    def __init__(
        self,
        keyword_classifier: KeywordClassifier,
        semantic_classifier: SemanticClassifier,
        resolver: ConflictResolver,
    ) -> None:
        self._keyword = keyword_classifier
        self._semantic = semantic_classifier
        self._resolver = resolver

    def classify(self, input_data: ClassificationInput) -> ClassificationResult:
      
        # Aşama 1: Keyword
        keyword_result = self._keyword.classify(input_data)

        if keyword_result is not None and keyword_result.confidence == 1.0:
            logger.debug(
                "classifier.service.keyword_only",
                extra={
                    "category": keyword_result.category.value,
                    "keywords": keyword_result.matched_keywords[:3],
                },
            )
            return keyword_result

        # Aşama 2: Semantic
        semantic_result = self._semantic.classify(input_data)

        # Aşama 3: Resolver
        final = self._resolver.resolve(keyword_result, semantic_result)

        logger.info(
            "classifier.service.result",
            extra={
                "news_id": input_data.news_id,
                "category": final.category.value,
                "confidence": final.confidence,
                "method": final.method,
            },
        )

        return final