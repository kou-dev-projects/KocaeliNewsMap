from __future__ import annotations

import logging

from .config import EmbeddingConfig, load_embedding_config
from .providers.bge_m3 import BGEM3Provider
from .providers.mock import MockImageProvider, MockTextProvider
from .providers.siglip2 import SigLIP2Provider
from .service import EmbeddingService


logger = logging.getLogger(__name__)


def build_embedding_service(
    config: EmbeddingConfig | None = None,
) -> EmbeddingService:
    cfg = config or load_embedding_config()

    match cfg.text_provider:
        case "mock":
            text = MockTextProvider()
        case "bge-m3":
            try:
                text = BGEM3Provider()
            except Exception as exc:
                logger.warning(
                    "embedding.factory.optional_provider_unavailable",
                    extra={
                        "provider": "bge-m3",
                        "error": f"{type(exc).__name__}: {exc}",
                    },
                )
                text = MockTextProvider()
        case _:
            raise ValueError(f"Bilinmeyen text provider: {cfg.text_provider!r}")

    match cfg.image_provider:
        case "mock":
            image = MockImageProvider()
        case "siglip2":
            try:
                image = SigLIP2Provider()
            except Exception as exc:
                logger.warning(
                    "embedding.factory.optional_provider_unavailable",
                    extra={
                        "provider": "siglip2",
                        "error": f"{type(exc).__name__}: {exc}",
                    },
                )
                image = MockImageProvider()
        case _:
            raise ValueError(f"Bilinmeyen image provider: {cfg.image_provider!r}")

    return EmbeddingService(
        text_provider=text,
        image_provider=image,
        config=cfg,
    )
