from __future__ import annotations

import logging

import httpx
import numpy as np


logger = logging.getLogger(__name__)


class _BaseRemoteProvider:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        provider: str,
        dimension: int,
    ) -> None:
        self._provider = provider
        self._dimension = dimension
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    def _post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        try:
            response = self._client.post(path, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error(
                "embedding.remote_provider.request_failed",
                extra={
                    "provider": self._provider,
                    "path": path,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            raise RuntimeError(
                f"ML service request failed for provider {self._provider!r}"
            ) from exc

        return response.json()


class RemoteTextProvider(_BaseRemoteProvider):
    @property
    def name(self) -> str:
        return f"remote-{self._provider}"

    def embed_text(self, text: str) -> np.ndarray:
        payload = self._post(
            "/embedding/text",
            {
                "provider": self._provider,
                "text": text,
                "dimension": self._dimension,
            },
        )
        return np.array(payload["vector"], dtype=np.float32)
