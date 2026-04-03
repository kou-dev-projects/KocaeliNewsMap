from __future__ import annotations


from ..schemas import RawEntity

try:
    from transformers import pipeline

    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class BERTTurkNERProvider:
    def __init__(self, model_name: str) -> None:
        if not _AVAILABLE:
            raise ImportError(
                "transformers yüklü değil. BERTTurk NER provider kullanılamaz."
            )
        self._model_name = model_name
        self._pipeline = None

    @property
    def name(self) -> str:
        return "bertturk-ner"

    def extract_entities(self, text: str) -> list[RawEntity]:
        if not text.strip():
            return []

        ner_pipeline = self._get_pipeline()
        outputs = ner_pipeline(text)

        entities: list[RawEntity] = []

        for item in outputs:
            label = item.get("entity_group") or item.get("entity") or ""
            word = item.get("word") or item.get("text") or ""
            score = float(item.get("score", 0.0))
            start = item.get("start")
            end = item.get("end")

            entities.append(
                RawEntity(
                    text=word,
                    label=label,
                    score=score,
                    start=int(start) if start is not None else None,
                    end=int(end) if end is not None else None,
                )
            )

        return entities

    def _get_pipeline(self):
        if not _AVAILABLE:
            raise ImportError(
                "transformers yüklü değil. BERTTurk NER provider kullanılamaz."
            )

        if self._pipeline is None:
            self._pipeline = pipeline(
                task="token-classification",
                model=self._model_name,
                tokenizer=self._model_name,
                aggregation_strategy="simple",
            )

        return self._pipeline
