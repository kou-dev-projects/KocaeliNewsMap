from __future__ import annotations
import json
import logging
import time
from pathlib import Path

import numpy as np

from .config import EmbeddingConfig
from .exceptions import VectorDimensionError
from .providers.base import TextProvider
from .schemas import (
    EmbeddingInput,
    TextEmbedding,
    DuplicateScore,
)
from app.utils.similarity import cosine_similarity

logger = logging.getLogger(__name__)


class EmbeddingService:

    def __init__(
        self,
        text_provider: TextProvider,
        config: EmbeddingConfig,
    ) -> None:
        self._text = text_provider
        self._cfg = config

   

    def embed(self, input_data: EmbeddingInput) -> TextEmbedding:
       
        start = time.monotonic()

        # --- Metin embedding ---
        text_payload = input_data.build_text_payload()
        text_vec = self._text.embed_text(text_payload)
        self._validate(text_vec, self._cfg.text_dimension, "text")

        text_emb = TextEmbedding(
            vector=text_vec.tolist(),
            dimension=int(len(text_vec)),
            provider=self._text.name,
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        self._log_cost(input_data, latency_ms)

        return text_emb

  

    def decide_duplicate(
        self,
        incoming_text: TextEmbedding,
        candidates: list[dict],
        new_source: str,
    ) -> DuplicateScore:
       
        if not candidates:
            return DuplicateScore(
                text_similarity=0.0,
                final_score=0.0,
                is_duplicate=False,
                debug={
                    "reason": "Karşılaştırılacak aday haber yok",
                    "threshold": self._cfg.duplicate_threshold,
                    "text_weight": self._cfg.text_score_weight,
                    "candidate_count": 0,
                },
            )

        best_final = 0.0
        best_text_sim = 0.0
        best_candidate: dict | None = None

        for candidate in candidates:
            # Metin benzerliği — her zaman hesaplanır
            try:
                text_sim = cosine_similarity(
                    incoming_text.vector,
                    candidate["text_vector"],
                )
            except ValueError:
                logger.warning(
                    "Boyut uyuşmazlığı — bu aday atlanıyor. id=%s",
                    candidate.get("id"),
                )
                continue

            final = self._cfg.text_score_weight * text_sim

            if final > best_final:
                best_final = final
                best_text_sim = text_sim
                best_candidate = candidate

        threshold = self._cfg.duplicate_threshold
        is_dup = best_final >= threshold

        merged: Optional[list[str]] = None
        if is_dup and best_candidate:
            existing: list[str] = best_candidate.get("kaynak_listesi", [])
            merged = (
                existing + [new_source]
                if new_source not in existing
                else existing
            )

        return DuplicateScore(
            text_similarity=round(best_text_sim, 4),
            final_score=round(best_final, 4),
            is_duplicate=is_dup,
            matched_news_id=best_candidate["id"] if is_dup and best_candidate else None,
            merged_kaynak_listesi=merged,
            debug={
                "threshold": threshold,
                "text_weight": self._cfg.text_score_weight,
                "candidate_count": len(candidates),
            },
        )

    def _validate(self, vec: np.ndarray, expected: int, label: str) -> None:
        if len(vec) != expected:
            raise VectorDimensionError(expected, len(vec))
        if np.any(np.isnan(vec)):
            raise ValueError(f"{label} vektöründe NaN tespit edildi")
        if np.any(np.isinf(vec)):
            raise ValueError(f"{label} vektöründe Inf tespit edildi")

    def _log_cost(self, input_data: EmbeddingInput, latency_ms: int) -> None:
        entry = {
            "text_provider": self._text.name,
            "latency_ms": latency_ms,
            **input_data.safe_log_repr(),
        }
        Path(self._cfg.cost_log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self._cfg.cost_log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")