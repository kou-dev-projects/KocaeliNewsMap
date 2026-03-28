from __future__ import annotations
import logging
from typing import Optional, TYPE_CHECKING

from .schemas import ClassificationInput, ClassificationResult, NewsCategory, CATEGORY_PRIORITY

if TYPE_CHECKING:
    from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


CATEGORY_PROTOTYPES: dict[NewsCategory, str] = {
    NewsCategory.TRAFIK_KAZASI: (
        "Kocaeli'de trafik kazası meydana geldi. "
        "Araçlar çarpıştı, yaralılar hastaneye kaldırıldı. "
        "Yol bir süre trafiğe kapandı."
    ),
    NewsCategory.YANGIN: (
        "Kocaeli'de yangın çıktı. "
        "İtfaiye ekipleri yangına müdahale etti. "
        "Duman nedeniyle bölge sakinleri tahliye edildi."
    ),
    NewsCategory.HIRSIZLIK: (
        "Kocaeli'de hırsızlık olayı yaşandı. "
        "Şüpheli gözaltına alındı. "
        "Çalınan eşyalar polis tarafından bulundu."
    ),
    NewsCategory.ELEKTRIK_KESINTISI: (
        "Kocaeli'de elektrik kesintisi yaşandı. "
        "KKEDAŞ ekipleri arızayı gidermek için çalışma başlattı. "
        "Saatlerce süren kesintide mahalle sakinleri mağdur oldu."
    ),
    NewsCategory.KULTUREL_ETKINLIK: (
        "Kocaeli'de kültürel etkinlik düzenlendi. "
        "Festival ve konser büyük ilgi gördü. "
        "Belediye tarafından organize edilen etkinliğe yoğun katılım oldu."
    ),
}


class SemanticClassifier:
    def __init__(
        self,
        embedding_service=None,
        threshold: float = 0.3,
    ) -> None:
        self._embedding_service = embedding_service
        self._threshold = threshold
        self._prototype_vectors = {}

    def classify(self, input_data: ClassificationInput) -> ClassificationResult:
        
        if self._embedding_service is None:
            return self._mock_classify(input_data)

        return self._semantic_classify(input_data)

    def _semantic_classify(
        self, input_data: ClassificationInput
    ) -> ClassificationResult:
        from app.utils.similarity import cosine_similarity

      
        self._ensure_prototypes()

        text_emb, _ = self._embedding_service.embed(
   
            self._to_embedding_input(input_data)
        )

        scores: dict[NewsCategory, float] = {}
        for category, proto_vec in self._prototype_vectors.items():
            try:
                scores[category] = cosine_similarity(text_emb.vector, proto_vec)
            except ValueError:
                scores[category] = 0.0

        best_category = max(scores, key=lambda c: scores[c])
        best_score = scores[best_category]

        logger.debug(
            "classifier.semantic.result",
            extra={
                "category": best_category.value,
                "confidence": round(best_score, 3),
                "scores": {k.value: round(v, 3) for k, v in scores.items()},
            },
        )

        return ClassificationResult(
            category=best_category if best_score > self._threshold else NewsCategory.UNKNOWN,
            confidence=round(best_score, 4),
            method="semantic",
            news_id=input_data.news_id,
            all_scores={k.value: round(v, 4) for k, v in scores.items()},
        )

    def _mock_classify(
        self, input_data: ClassificationInput
    ) -> ClassificationResult:
     
        from .keywords import CATEGORY_KEYWORDS

        text = input_data.full_text().lower()
        scores: dict[NewsCategory, float] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text)
            scores[category] = count / max(len(keywords), 1)

        best = max(scores, key=lambda c: scores[c])
        best_score = scores[best]

        return ClassificationResult(
            category=best if best_score > 0.0 else NewsCategory.UNKNOWN,
            confidence=round(best_score, 4),
            method="semantic_mock",
            news_id=input_data.news_id,
            all_scores={k.value: round(v, 4) for k, v in scores.items()},
        )

    def _ensure_prototypes(self) -> None:
        
        if self._prototype_vectors:
            return

        from app.services.embedding.schemas import EmbeddingInput

        for category, text in CATEGORY_PROTOTYPES.items():
            inp = EmbeddingInput(
                title=text[:100],
                content=text,
                source="prototype",
            )
            text_emb, _ = self._embedding_service.embed(inp)
            self._prototype_vectors[category] = text_emb.vector

        logger.info(
            "classifier.semantic.prototypes_ready",
            extra={"count": len(self._prototype_vectors)},
        )

    def _to_embedding_input(self, input_data: ClassificationInput):
        from app.services.embedding.schemas import EmbeddingInput
        return EmbeddingInput(
            title=input_data.title,
            summary=input_data.summary,
            content=input_data.content,
            source="classifier",
        )