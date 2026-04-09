from __future__ import annotations

import logging
from functools import lru_cache

from .config import NERConfig
from .providers.bertturk import BERTTurkNERProvider
from .providers.gliner_tagger import GLiNERTagger
from .providers.mock import MockNERProvider
from .service import NERService


logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def _build_local_ner_service_cached(
    config: NERConfig,
    allow_fallback: bool,
) -> NERService:
    match config.provider:
        case "mock":
            provider = MockNERProvider()
        case "bertturk":
            try:
                provider = BERTTurkNERProvider(model_name=config.model_name)
            except ImportError as exc:
                if not allow_fallback:
                    raise
                logger.warning(
                    "ner.factory.optional_provider_unavailable",
                    extra={"provider": "bertturk", "error": str(exc)},
                )
                provider = MockNERProvider()
        case "gliner":
            try:
                provider = GLiNERTagger(
                    model_name=config.model_name or "urchade/gliner_multi-v2.1",
                    threshold=config.gliner_threshold,
                )
            except ImportError as exc:
                if not allow_fallback:
                    raise
                logger.warning(
                    "ner.factory.optional_provider_unavailable",
                    extra={"provider": "gliner", "error": str(exc)},
                )
                provider = MockNERProvider()
        case _:
            raise ValueError(f"Bilinmeyen NER provider: {config.provider!r}")

    return NERService(
        provider=provider,
        min_score=config.min_score,
    )


def build_local_ner_service(
    config: NERConfig,
    *,
    allow_fallback: bool = True,
) -> NERService:
    return _build_local_ner_service_cached(config, allow_fallback)
