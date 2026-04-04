from __future__ import annotations

from app.settings import settings

from .config import EmbeddingConfig, load_embedding_config
from .local_factory import build_local_image_provider, build_local_text_provider
from .providers.remote import RemoteImageProvider, RemoteTextProvider
from .service import EmbeddingService

def build_text_provider(config: EmbeddingConfig):
    if settings.ml_service_url and config.text_provider != "mock":
        return RemoteTextProvider(
            base_url=settings.ml_service_url,
            timeout_seconds=settings.ml_service_timeout_seconds,
            provider=config.text_provider,
            dimension=config.text_dimension,
        )
    return build_local_text_provider(config)


def build_image_provider(config: EmbeddingConfig):
    if settings.ml_service_url and config.image_provider != "mock":
        return RemoteImageProvider(
            base_url=settings.ml_service_url,
            timeout_seconds=settings.ml_service_timeout_seconds,
            provider=config.image_provider,
            dimension=config.image_dimension,
        )
    return build_local_image_provider(config)


def build_embedding_service(
    config: EmbeddingConfig | None = None,
) -> EmbeddingService:
    cfg = config or load_embedding_config()
    text = build_text_provider(cfg)
    image = build_image_provider(cfg)

    return EmbeddingService(
        text_provider=text,
        image_provider=image,
        config=cfg,
    )
