from __future__ import annotations

from dataclasses import replace
import logging
from typing import Optional

from app.domain.enums import NewsCategory

from .schemas import CATEGORY_PRIORITY, ClassificationResult

logger = logging.getLogger(__name__)

_KEYWORD_WINS_THRESHOLD = 0.18
_SEMANTIC_WINS_THRESHOLD = 0.12
_SEMANTIC_UNKNOWN_THRESHOLD = 0.55
_WEAK_KEYWORD_THRESHOLD = 0.60
_AMBIGUITY_THRESHOLD = 0.06


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

        if semantic_result.category == NewsCategory.UNKNOWN:
            if (
                semantic_result.confidence >= _SEMANTIC_UNKNOWN_THRESHOLD
                and keyword_result.confidence <= _WEAK_KEYWORD_THRESHOLD
            ):
                return replace(
                    semantic_result,
                    method="resolver_semantic_unknown",
                    news_id=keyword_result.news_id,
                    all_scores=self._merge_scores(keyword_result, semantic_result),
                )
            return replace(
                keyword_result,
                method="resolver_keyword",
                all_scores=self._merge_scores(keyword_result, semantic_result),
            )

        if keyword_result.category == NewsCategory.UNKNOWN:
            return replace(
                semantic_result,
                method="resolver_semantic",
                news_id=keyword_result.news_id,
                all_scores=self._merge_scores(keyword_result, semantic_result),
            )

        semantic_advantage = semantic_result.confidence - keyword_result.confidence
        if semantic_advantage >= _SEMANTIC_WINS_THRESHOLD:
            return replace(
                semantic_result,
                method="resolver_semantic",
                news_id=keyword_result.news_id,
                all_scores=self._merge_scores(keyword_result, semantic_result),
            )

        keyword_advantage = keyword_result.confidence - semantic_result.confidence
        if keyword_advantage >= _KEYWORD_WINS_THRESHOLD:
            return replace(
                keyword_result,
                method="resolver_keyword",
                all_scores=self._merge_scores(keyword_result, semantic_result),
            )

        if abs(semantic_advantage) <= _AMBIGUITY_THRESHOLD:
            kw_priority = CATEGORY_PRIORITY.get(keyword_result.category, 99)
            sem_priority = CATEGORY_PRIORITY.get(semantic_result.category, 99)
            winner = keyword_result if kw_priority <= sem_priority else semantic_result
            return replace(
                winner,
                method="resolver_priority",
                news_id=keyword_result.news_id,
                all_scores=self._merge_scores(keyword_result, semantic_result),
            )

        winner = semantic_result if semantic_advantage > 0 else keyword_result
        return replace(
            winner,
            method="resolver_semantic" if winner is semantic_result else "resolver_keyword",
            news_id=keyword_result.news_id,
            all_scores=self._merge_scores(keyword_result, semantic_result),
        )

    def _merge_scores(
        self,
        kw: ClassificationResult,
        sem: ClassificationResult,
    ) -> dict[str, float]:
        merged = {**sem.all_scores}
        for key, value in kw.all_scores.items():
            merged[key] = max(merged.get(key, 0.0), value)
        return merged
