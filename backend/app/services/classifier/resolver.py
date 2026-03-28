from __future__ import annotations
from dataclasses import replace
import logging
from typing import Optional

from .schemas import (
    ClassificationResult,
    NewsCategory,
    CATEGORY_PRIORITY,
)

logger = logging.getLogger(__name__)

_CONFIDENCE_THRESHOLD = 0.15  


class ConflictResolver:

    def resolve(
        self,
        keyword_result: Optional[ClassificationResult],
        semantic_result: ClassificationResult,
    ) -> ClassificationResult:
      
       
        if keyword_result is None:
            return replace(semantic_result, method="semantic")

        
        if keyword_result.category == semantic_result.category:
            avg_confidence = (
                keyword_result.confidence + semantic_result.confidence
            ) / 2
            return ClassificationResult(
                category=keyword_result.category,
                confidence=round(avg_confidence, 4),
                method="resolver_agree",
                news_id=keyword_result.news_id,
                matched_keywords=keyword_result.matched_keywords,
                all_scores=self._merge_scores(keyword_result, semantic_result),
            )

        conf_diff = keyword_result.confidence - semantic_result.confidence
        if conf_diff >= _CONFIDENCE_THRESHOLD:
            logger.debug(
                "classifier.resolver.keyword_wins",
                extra={
                    "keyword_cat": keyword_result.category.value,
                    "semantic_cat": semantic_result.category.value,
                    "conf_diff": round(conf_diff, 3),
                },
            )
            return replace(keyword_result, method="resolver_keyword")

        kw_priority = CATEGORY_PRIORITY.get(keyword_result.category, 99)
        sem_priority = CATEGORY_PRIORITY.get(semantic_result.category, 99)

        winner = keyword_result if kw_priority <= sem_priority else semantic_result

        logger.debug(
            "classifier.resolver.priority_wins",
            extra={
                "winner": winner.category.value,
                "kw_priority": kw_priority,
                "sem_priority": sem_priority,
            },
        )

        return replace(winner, method="resolver_priority")

    def _merge_scores(
        self,
        kw: ClassificationResult,
        sem: ClassificationResult,
    ) -> dict[str, float]:
        merged = {**sem.all_scores}
        for k, v in kw.all_scores.items():
            merged[k] = max(merged.get(k, 0.0), v)
        return merged