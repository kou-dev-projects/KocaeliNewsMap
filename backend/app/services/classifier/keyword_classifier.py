from __future__ import annotations
import logging
from typing import Optional

from .keywords import CATEGORY_KEYWORDS
from .schemas import (
    ClassificationInput,
    ClassificationResult,
    NewsCategory,
    CATEGORY_PRIORITY,
)
logger = logging.getLogger(__name__)


class KeywordClassifier:

    def classify(
        self, input_data: ClassificationInput
    ) -> Optional[ClassificationResult]:
  
        text = input_data.full_text().lower()
        matches: dict[NewsCategory, list[str]] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            found = [kw for kw in keywords if kw in text]
            if found:
                matches[category] = found

        if not matches:
            return None

        
        best_category = min(
            matches.keys(),
            key=lambda c: CATEGORY_PRIORITY.get(c, 99),
        )

        result = ClassificationResult(
            category=best_category,
            confidence=1.0,
            method="keyword",
            news_id=input_data.news_id,
            matched_keywords=matches[best_category],
            all_scores={
                cat.value: 1.0 for cat in matches
            },
        )

        logger.debug(
            "classifier.keyword.match",
            extra={
                "category": best_category.value,
                "keywords": matches[best_category][:5],
                "total_matches": len(matches),
            },
        )

        return result