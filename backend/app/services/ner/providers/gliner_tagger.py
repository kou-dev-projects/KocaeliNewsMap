from __future__ import annotations
import logging
from typing import Optional

from ..schemas import RawEntity

logger = logging.getLogger(__name__)


GLINER_LABELS = [
    "il",
    "ilçe",
    "mahalle",
    "etkinlik",
    "mekan",
    "kurum",
    "sokak",
    "cadde",
]

try:
    from gliner import GLiNER as _GLiNER
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class GLiNERTagger:
    name = "gliner"

    def __init__(
        self,
        model_name: str = "urchade/gliner_multi-v2.1",
        labels: Optional[list[str]] = None,
        threshold: float = 0.5,
    ) -> None:
        if not _AVAILABLE:
            raise ImportError(
                "gliner kurulu değil: pip install gliner"
            )
        self._model_name = model_name
        self._labels = labels or GLINER_LABELS
        self._threshold = threshold
        self._model = None

    def extract_entities(self, text: str) -> list[RawEntity]:
        if not text.strip():
            return []

        model = self._get_model()
        entities = model.predict_entities(
            text,
            self._labels,
            threshold=self._threshold,
        )

        results = []
        for ent in entities:
            results.append(
                RawEntity(
                    text=ent["text"],
                    label=ent["label"],
                    score=float(ent["score"]),
                    start=ent.get("start"),
                    end=ent.get("end"),
                )
            )

        logger.debug(
            "ner.gliner.result",
            extra={
                "entity_count": len(results),
                "labels_used": self._labels,
            },
        )
        return results

    def _get_model(self):
        if self._model is None:
            logger.info(
                "ner.gliner.loading",
                extra={"model": self._model_name},
            )
            self._model = _GLiNER.from_pretrained(self._model_name)
        return self._model