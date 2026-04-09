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
        semantic_enabled: bool = True,
        keyword_only_mode: bool = False,
    ) -> None:
        self._keyword = keyword_classifier
        self._semantic = semantic_classifier
        self._resolver = resolver
        self._semantic_enabled = semantic_enabled
        self._keyword_only_mode = keyword_only_mode

    def classify(self, input_data: ClassificationInput) -> ClassificationResult:
        keyword_result = self._keyword.classify(input_data)

        if self._keyword_only_mode or not self._semantic_enabled:
            logger.debug(
                "classifier.service.semantic_skipped",
                extra={
                    "keyword_only_mode": self._keyword_only_mode,
                    "semantic_enabled": self._semantic_enabled,
                    "keyword_category": keyword_result.category.value if keyword_result else None,
                },
            )
            if keyword_result is not None:
                return keyword_result

            return ClassificationResult(
                category=NewsCategory.UNKNOWN,
                confidence=0.0,
                method="keyword_only",
                news_id=input_data.news_id,
            )

        try:
            semantic_result = self._semantic.classify(input_data)
        except Exception as exc:
            logger.warning(
                "classifier.service.semantic_failed",
                extra={
                    "news_id": input_data.news_id,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            if keyword_result is not None:
                return ClassificationResult(
                    category=keyword_result.category,
                    confidence=keyword_result.confidence,
                    method="keyword_fallback_semantic_error",
                    news_id=input_data.news_id,
                    matched_keywords=keyword_result.matched_keywords,
                    all_scores=keyword_result.all_scores,
                )

            return ClassificationResult(
                category=NewsCategory.UNKNOWN,
                confidence=0.0,
                method="semantic_error_unknown",
                news_id=input_data.news_id,
            )

        final = self._resolver.resolve(keyword_result, semantic_result)

        logger.info(
            "classifier.service.result",
            extra={
                "news_id": input_data.news_id,
                "category": final.category.value,
                "confidence": final.confidence,
                "method": final.method,
                "keyword_category": keyword_result.category.value if keyword_result else None,
                "semantic_category": semantic_result.category.value,
            },
        )

        return final
