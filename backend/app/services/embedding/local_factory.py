from __future__ import annotations

import logging
from functools import lru_cache

from .config import EmbeddingConfig
from .providers.bge_m3 import BGEM3Provider
from .providers.mock import MockTextProvider


logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def _build_local_text_provider_cached(
    config: EmbeddingConfig,
    allow_fallback: bool,
):
    match config.text_provider:
        case "mock":
            return MockTextProvider()
        case "bge-m3":
            try:
                return BGEM3Provider()
            except Exception as exc:
                if not allow_fallback:
                    raise
                logger.warning(
                    "embedding.factory.optional_provider_unavailable",
                    extra={
                        "provider": "bge-m3",
                        "error": f"{type(exc).__name__}: {exc}",
                    },
                )
                return MockTextProvider()
        case _:
            raise ValueError(f"Bilinmeyen text provider: {config.text_provider!r}")


def build_local_text_provider(
    config: EmbeddingConfig,
    *,
    allow_fallback: bool = True,
):
    return _build_local_text_provider_cached(config, allow_fallback)
