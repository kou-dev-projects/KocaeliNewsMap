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
    _SEGMENT_WEIGHTS = {
        "title": 3.0,
        "summary": 1.5,
        "content": 1.0,
    }
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
        segments = self._build_segments(input_data)
        matches: dict[NewsCategory, list[str]] = {}
        scores: dict[NewsCategory, float] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            found: list[str] = []
            weighted_score = 0.0

            for keyword in keywords:
                keyword_score = 0.0
                for segment_name, (text, tokens) in segments.items():
                    if self._matches_keyword(keyword=keyword, text=text, tokens=tokens):
                        keyword_score += self._SEGMENT_WEIGHTS[segment_name]
                if keyword_score <= 0:
                    continue

                found.append(self._normalize_text(keyword.lower()))
                weighted_score += keyword_score

            if found:
                matches[category] = found
                scores[category] = weighted_score

        if not matches:
            return None

        best_category = max(
            matches.keys(),
            key=lambda c: (scores[c], -CATEGORY_PRIORITY.get(c, 99)),
        )

        result = ClassificationResult(
            category=best_category,
            confidence=1.0,
            method="keyword",
            news_id=input_data.news_id,
            matched_keywords=matches[best_category],
            all_scores={
                cat.value: round(scores[cat], 3) for cat in matches
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

    def _build_segments(
        self,
        input_data: ClassificationInput,
    ) -> dict[str, tuple[str, set[str]]]:
        raw_segments = {
            "title": input_data.title or "",
            "summary": input_data.summary or "",
            "content": (input_data.content or "")[:1000],
        }
        built: dict[str, tuple[str, set[str]]] = {}
        for name, raw_value in raw_segments.items():
            text = self._normalize_text(raw_value.lower())
            built[name] = (text, set(self._TOKEN_PATTERN.findall(text)))
        return built

    def _matches_keyword(self, *, keyword: str, text: str, tokens: set[str]) -> bool:
        normalized_keyword = self._normalize_text(keyword.lower())

        if " " not in normalized_keyword:
            return any(
                self._token_matches_keyword(token=token, keyword=normalized_keyword)
                for token in tokens
            )

        escaped_keyword = re.escape(normalized_keyword)
        pattern = rf"(?<!\w){escaped_keyword}(?!\w)"
        if re.search(pattern, text, flags=re.UNICODE) is not None:
            return True

        keyword_tokens = normalized_keyword.split()
        text_tokens = self._TOKEN_PATTERN.findall(text)
        window_size = len(keyword_tokens)
        if len(text_tokens) < window_size:
            return False

        for start_index in range(len(text_tokens) - window_size + 1):
            window = text_tokens[start_index : start_index + window_size]
            if all(
                self._token_matches_keyword(
                    token=window[idx],
                    keyword=keyword_tokens[idx],
                )
                for idx in range(window_size)
            ):
                return True

        return False

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
