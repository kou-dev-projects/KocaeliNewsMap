from __future__ import annotations
import logging
import re
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
    _TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)
    _WHITESPACE_PATTERN = re.compile(r"\s+")
    _TURKISH_SUFFIXES = tuple(
        sorted(
            {
                "larda", "lerde", "lardan", "lerden",
                "daki", "deki", "taki", "teki",
                "ların", "lerin", "ların", "lerin",
                "lardan", "lerden", "lardan", "lerden",
                "sında", "sinde", "sunda", "sünde",
                "sına", "sine", "suna", "süne",
                "sıyla", "siyle", "suyla", "süyle",
                "larınca", "lerince",
                "ndan", "nden", "ntan", "nten",
                "yla", "yle", "dan", "den", "tan", "ten",
                "nda", "nde", "na", "ne", "da", "de", "ta", "te",
                "nın", "nin", "nun", "nün",
                "ın", "in", "un", "ün",
                "yı", "yi", "yu", "yü",
                "sı", "si", "su", "sü",
                "lar", "ler",
                "ya", "ye", "a", "e", "ı", "i", "u", "ü",
            },
            key=len,
            reverse=True,
        )
    )

    def classify(
        self, input_data: ClassificationInput
    ) -> Optional[ClassificationResult]:
        raw_text = input_data.full_text().lower()
        text = self._normalize_text(raw_text)
        tokens = set(self._TOKEN_PATTERN.findall(text))
        matches: dict[NewsCategory, list[str]] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            found = [
                kw for kw in keywords
                if self._matches_keyword(keyword=kw, text=text, tokens=tokens)
            ]
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

    def _matches_keyword(self, *, keyword: str, text: str, tokens: set[str]) -> bool:
        normalized_keyword = self._normalize_text(keyword.lower())

        if " " not in normalized_keyword:
            return any(
                self._token_matches_keyword(token=token, keyword=normalized_keyword)
                for token in tokens
            )

        escaped_keyword = re.escape(normalized_keyword)
        pattern = rf"(?<!\w){escaped_keyword}(?!\w)"
        return re.search(pattern, text, flags=re.UNICODE) is not None

    def _normalize_text(self, value: str) -> str:
        repaired = self._repair_mojibake(value)
        return self._WHITESPACE_PATTERN.sub(" ", repaired).strip().lower()

    def _repair_mojibake(self, value: str) -> str:
        try:
            return value.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value

    def _token_matches_keyword(self, *, token: str, keyword: str) -> bool:
        if token == keyword:
            return True

        if len(keyword) <= 3 or not token.startswith(keyword):
            return False

        remainder = token[len(keyword):]
        return self._matches_suffix_chain(remainder)

    def _matches_suffix_chain(self, remainder: str) -> bool:
        if not remainder:
            return True

        for suffix in self._TURKISH_SUFFIXES:
            if remainder.startswith(suffix) and self._matches_suffix_chain(
                remainder[len(suffix):]
            ):
                return True

        return False
