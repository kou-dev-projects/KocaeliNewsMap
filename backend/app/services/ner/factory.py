from __future__ import annotations

from .config import NERConfig, load_ner_config
from .providers.bertturk import BERTTurkNERProvider
from .providers.mock import MockNERProvider
from .service import NERService


def build_ner_service(
    config: NERConfig | None = None,
) -> NERService:
    cfg = config or load_ner_config()

    match cfg.provider:
        case "mock":
            provider = MockNERProvider()
        case "bertturk":
            provider = BERTTurkNERProvider(model_name=cfg.model_name)
        case _:
            raise ValueError(f"Bilinmeyen NER provider: {cfg.provider!r}")

    return NERService(
        provider=provider,
        min_score=cfg.min_score,
    )
