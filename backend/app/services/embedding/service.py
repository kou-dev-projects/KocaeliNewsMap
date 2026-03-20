from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np

from .config import EmbeddingConfig
from .exceptions import VectorDimensionError
from .providers.base import TextProvider, ImageProvider
from .schemas import (
    EmbeddingInput,
    TextEmbedding,
    ImageEmbedding,
    DuplicateScore,
)
from app.utils.similarity import cosine_similarity

logger = logging.getLogger(__name__)


class EmbeddingService:

    def __init__(
        self,
        text_provider: TextProvider,
        image_provider: ImageProvider,
        config: EmbeddingConfig,
    ) -> None:
        self._text = text_provider
        self._image = image_provider
        self._cfg = config

   

    def embed(
        self, input_data: EmbeddingInput
    ) -> tuple[TextEmbedding, ImageEmbedding | None]:
       
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

        # --- Görsel embedding ---
        image_emb: ImageEmbedding | None = None
        if input_data.image_url:
            image_vec = self._safe_embed_image(input_data.image_url)
            if image_vec is not None:
                self._validate(image_vec, self._cfg.image_dimension, "image")
                image_emb = ImageEmbedding(
                    vector=image_vec.tolist(),
                    dimension=int(len(image_vec)),
                    provider=self._image.name,
                )

        latency_ms = int((time.monotonic() - start) * 1000)
        self._log_cost(input_data, latency_ms, has_image=image_emb is not None)

        return text_emb, image_emb

  

    def decide_duplicate(
        self,
        incoming_text: TextEmbedding,
        incoming_image: ImageEmbedding | None,
        candidates: list[dict],
        new_source: str,
    ) -> DuplicateScore:
       
        if not candidates:
            return DuplicateScore(
                text_similarity=0.0,
                image_similarity=None,
                final_score=0.0,
                is_duplicate=False,
                debug={
                    "reason": "Karşılaştırılacak aday haber yok",
                    "threshold": self._cfg.duplicate_threshold,
                    "text_weight": self._cfg.text_score_weight,
                    "image_weight": self._cfg.image_score_weight,
                    "image_used": False,
                    "candidate_count": 0,
                },
            )

        best_final = 0.0
        best_text_sim = 0.0
        best_image_sim: Optional[float] = None
        best_candidate: Optional[dict] = None

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

            # Görsel benzerliği — her iki tarafta da görsel varsa
            image_sim: Optional[float] = None
            if (
                incoming_image is not None
                and candidate.get("image_vector") is not None
            ):
                try:
                    image_sim = cosine_similarity(
                        incoming_image.vector,
                        candidate["image_vector"],
                    )
                except ValueError:
                    image_sim = None

            # Skor birleştirme
            if image_sim is not None:
                final = (
                    self._cfg.text_score_weight * text_sim
                    + self._cfg.image_score_weight * image_sim
                )
            else:
                final = text_sim   # görsel yoksa sadece metin skoru

            if final > best_final:
                best_final = final
                best_text_sim = text_sim
                best_image_sim = image_sim
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
            image_similarity=round(best_image_sim, 4) if best_image_sim is not None else None,
            final_score=round(best_final, 4),
            is_duplicate=is_dup,
            matched_news_id=best_candidate["id"] if is_dup and best_candidate else None,
            merged_kaynak_listesi=merged,
            debug={
                "threshold": threshold,
                "text_weight": self._cfg.text_score_weight,
                "image_weight": self._cfg.image_score_weight,
                "image_used": best_image_sim is not None,
                "candidate_count": len(candidates),
            },
        )
    
    def _safe_embed_image(self, image_url: str) -> np.ndarray | None:
        try:
            return self._image.embed_image(image_url)
        except Exception as exc:
            logger.warning(
                "Görsel embedding başarısız — metin embedding devam eder. "
                "provider=%s hata_tipi=%s",
                self._image.name,
                type(exc).__name__,
            )
            return None

    def _validate(self, vec: np.ndarray, expected: int, label: str) -> None:
        if len(vec) != expected:
            raise VectorDimensionError(expected, len(vec))
        if np.any(np.isnan(vec)):
            raise ValueError(f"{label} vektöründe NaN tespit edildi")
        if np.any(np.isinf(vec)):
            raise ValueError(f"{label} vektöründe Inf tespit edildi")

    def _log_cost(
        self, input_data: EmbeddingInput, latency_ms: int, has_image: bool
    ) -> None:
        entry = {
            "text_provider": self._text.name,
            "image_provider": self._image.name,
            "latency_ms": latency_ms,
            "has_image": has_image,
            **input_data.safe_log_repr(),
        }
        Path(self._cfg.cost_log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self._cfg.cost_log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")