from __future__ import annotations
from .config import EmbeddingConfig, load_embedding_config
from .providers.mock import MockTextProvider, MockImageProvider
from .providers.bge_m3 import BGEM3Provider
from .providers.siglip2 import SigLIP2Provider
from .service import EmbeddingService


def build_embedding_service(
    config: EmbeddingConfig | None = None,
) -> EmbeddingService:
    cfg = config or load_embedding_config()

    match cfg.text_provider:
        case "mock":
            text = MockTextProvider()
        case "bge-m3":
            text = BGEM3Provider()
        case _:
            raise ValueError(f"Bilinmeyen text provider: {cfg.text_provider!r}")

    match cfg.image_provider:
        case "mock":
            image = MockImageProvider()
        case "siglip2":
            image = SigLIP2Provider()
        case _:
            raise ValueError(f"Bilinmeyen image provider: {cfg.image_provider!r}")

    return EmbeddingService(
        text_provider=text,
        image_provider=image,
        config=cfg,
    )