from __future__ import annotations

import logging

from .config import NERConfig, load_ner_config
from .providers.bertturk import BERTTurkNERProvider
from .providers.gliner_tagger import GLiNERTagger
from .providers.mock import MockNERProvider
from .service import NERService


logger = logging.getLogger(__name__)


def build_ner_service(
    config: NERConfig | None = None,
) -> NERService:
    cfg = config or load_ner_config()

    match cfg.provider:
        case "mock":
            provider = MockNERProvider()
        case "bertturk":
            try:
                provider = BERTTurkNERProvider(model_name=cfg.model_name)
            except ImportError as exc:
                logger.warning(
                    "ner.factory.optional_provider_unavailable",
                    extra={"provider": "bertturk", "error": str(exc)},
                )
                provider = MockNERProvider()
        case "gliner":
            try:
                provider = GLiNERTagger(
                    model_name=cfg.model_name or "urchade/gliner_multi-v2.1",
                    threshold=cfg.gliner_threshold,
                )
            except ImportError as exc:
                logger.warning(
                    "ner.factory.optional_provider_unavailable",
                    extra={"provider": "gliner", "error": str(exc)},
                )
                provider = MockNERProvider()
        case _:
            raise ValueError(f"Bilinmeyen NER provider: {cfg.provider!r}")

    return NERService(
        provider=provider,
        min_score=cfg.min_score,
    )
