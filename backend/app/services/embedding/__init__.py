from .service import EmbeddingService


def build_embedding_service(*args, **kwargs):
    from .factory import build_embedding_service as _build_embedding_service

    return _build_embedding_service(*args, **kwargs)

__all__ = ["EmbeddingService", "build_embedding_service"]
