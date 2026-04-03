from __future__ import annotations

import logging

import httpx

from .config import NERConfig
from .schemas import LocationCandidate, NERInput, NERResult, RawEntity


logger = logging.getLogger(__name__)


class RemoteNERService:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        config: NERConfig,
    ) -> None:
        self._config = config
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
        )

    def extract_locations(self, input_data: NERInput) -> NERResult:
        try:
            response = self._client.post(
                "/ner/extract-locations",
                json={
                    "provider": self._config.provider,
                    "model_name": self._config.model_name,
                    "min_score": self._config.min_score,
                    "gliner_threshold": self._config.gliner_threshold,
                    "title": input_data.title,
                    "summary": input_data.summary,
                    "content": input_data.content,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error(
                "ner.remote_service.request_failed",
                extra={
                    "provider": self._config.provider,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            raise RuntimeError(
                f"ML service request failed for NER provider {self._config.provider!r}"
            ) from exc

        payload = response.json()
        return NERResult(
            raw_entities=[
                RawEntity(**item) for item in payload.get("raw_entities", [])
            ],
            location_candidates=[
                LocationCandidate(**item)
                for item in payload.get("location_candidates", [])
            ],
            validated_districts=payload.get("validated_districts", []),
            provider=payload.get("provider", f"remote-{self._config.provider}"),
        )
