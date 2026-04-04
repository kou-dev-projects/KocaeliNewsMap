from __future__ import annotations

import logging

import numpy as np

from ..exceptions import ProviderUnavailableError

logger = logging.getLogger(__name__)

try:
    from FlagEmbedding import BGEM3FlagModel
    import torch

    _AVAILABLE = True
except ImportError:
    torch = None
    _AVAILABLE = False


class BGEM3Provider:
    name = "bge-m3"
    dimension = 1024

    def __init__(self) -> None:
        if not _AVAILABLE:
            raise ProviderUnavailableError(
                "FlagEmbedding yüklü değil. BGE-M3 kullanmak için FlagEmbedding bağımlılığını kurun."
            )
        self._model: BGEM3FlagModel | None = None

    def embed_text(self, text: str) -> np.ndarray:
        model = self._get_model()

        output = model.encode(
            text,
            batch_size=1,
            max_length=8192,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )

        vec = np.array(output["dense_vecs"], dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def _get_model(self) -> BGEM3FlagModel:
        if self._model is None:
            logger.info("BGE-M3 modeli yükleniyor")
            self._model = BGEM3FlagModel(
                "BAAI/bge-m3",
                use_fp16=bool(torch is not None and torch.cuda.is_available()),
            )
        return self._model
