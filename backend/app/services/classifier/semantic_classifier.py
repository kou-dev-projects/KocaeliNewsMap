from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from .schemas import ClassificationInput, ClassificationResult, NewsCategory
from .semantic_exemplars import CATEGORY_EXEMPLARS

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SemanticClassifier:
    def __init__(
        self,
        embedding_service=None,
        threshold: float = 0.3,
        margin_threshold: float = 0.08,
        exemplar_catalog: dict[NewsCategory, tuple[str, ...]] | None = None,
    ) -> None:
        self._embedding_service = embedding_service
        self._threshold = threshold
        self._margin_threshold = margin_threshold
        self._exemplar_catalog = exemplar_catalog or CATEGORY_EXEMPLARS
        self._prototype_vectors: dict[NewsCategory, list[list[float]]] = {}
        self._prototype_centroids: dict[NewsCategory, list[float]] = {}

    def classify(self, input_data: ClassificationInput) -> ClassificationResult:
        if self._embedding_service is None:
            return self._mock_classify(input_data)

        return self._semantic_classify(input_data)

    def _semantic_classify(
        self,
        input_data: ClassificationInput,
    ) -> ClassificationResult:
        from app.utils.similarity import cosine_similarity

        self._ensure_prototypes()

        text_emb = self._embedding_service.embed(
            self._to_embedding_input(input_data)
        )

        scores: dict[NewsCategory, float] = {}
        for category, proto_vecs in self._prototype_vectors.items():
            try:
                exemplar_score = max(
                    cosine_similarity(text_emb.vector, proto_vec)
                    for proto_vec in proto_vecs
                )
                centroid_score = cosine_similarity(
                    text_emb.vector,
                    self._prototype_centroids[category],
                )
            except ValueError:
                scores[category] = 0.0
                continue

            scores[category] = round((0.7 * exemplar_score) + (0.3 * centroid_score), 4)

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_category, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        score_margin = round(best_score - second_score, 4)

        if best_score < self._threshold:
            final_category = NewsCategory.UNKNOWN
        elif best_category != NewsCategory.UNKNOWN and score_margin < self._margin_threshold:
            final_category = NewsCategory.UNKNOWN
        else:
            final_category = best_category

        logger.debug(
            "classifier.semantic.result",
            extra={
                "category": final_category.value,
                "confidence": round(best_score, 3),
                "margin": score_margin,
                "scores": {k.value: round(v, 3) for k, v in scores.items()},
            },
        )

        return ClassificationResult(
            category=final_category,
            confidence=round(best_score, 4),
            method="semantic",
            news_id=input_data.news_id,
            all_scores={k.value: round(v, 4) for k, v in scores.items()},
        )

    def _mock_classify(
        self,
        input_data: ClassificationInput,
    ) -> ClassificationResult:
        from .keywords import CATEGORY_KEYWORDS

        text = input_data.full_text().lower()
        scores: dict[NewsCategory, float] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            count = sum(1 for keyword in keywords if keyword in text)
            scores[category] = count / max(len(keywords), 1)

        best = max(scores, key=lambda category: scores[category])
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

        for category, exemplars in self._exemplar_catalog.items():
            vectors: list[list[float]] = []
            for index, text in enumerate(exemplars):
                embedding_input = EmbeddingInput(
                    title=f"{category.value}_{index}",
                    content=text,
                    source="prototype",
                )
                embedding = self._embedding_service.embed(embedding_input)
                vectors.append(embedding.vector)

            self._prototype_vectors[category] = vectors
            self._prototype_centroids[category] = (
                np.mean(np.array(vectors, dtype=np.float32), axis=0).tolist()
            )

        logger.info(
            "classifier.semantic.prototypes_ready",
            extra={
                "count": len(self._prototype_vectors),
                "exemplar_count": sum(
                    len(vectors) for vectors in self._prototype_vectors.values()
                ),
            },
        )

    def _to_embedding_input(self, input_data: ClassificationInput):
        from app.services.embedding.schemas import EmbeddingInput

        return EmbeddingInput(
            title=input_data.title,
            summary=input_data.summary,
            content=input_data.content,
            source="classifier",
        )
