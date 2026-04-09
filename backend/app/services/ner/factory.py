from __future__ import annotations

from app.settings import settings

from .config import NERConfig, load_ner_config
from .local_factory import build_local_ner_service
from .remote_service import RemoteNERService
from .service import NERService

def build_ner_service(
    config: NERConfig | None = None,
) -> NERService | RemoteNERService:
    cfg = config or load_ner_config()
    if settings.ml_service_url and cfg.provider != "mock":
        return RemoteNERService(
            base_url=settings.ml_service_url,
            timeout_seconds=settings.ml_service_timeout_seconds,
            config=cfg,
        )
    return build_local_ner_service(cfg)
