from .service import NERService


def build_ner_service(*args, **kwargs):
    from .factory import build_ner_service as _build_ner_service

    return _build_ner_service(*args, **kwargs)

__all__ = ["NERService", "build_ner_service"]
