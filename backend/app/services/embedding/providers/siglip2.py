from __future__ import annotations
import logging
from io import BytesIO
from typing import Optional

import numpy as np
import requests

from ..exceptions import ImageFetchError

logger = logging.getLogger(__name__)

_MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10MB
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_TIMEOUT_SECONDS = 10
_MAX_REDIRECTS = 3

try:
    import torch
    from PIL import Image
    from transformers import AutoProcessor, AutoModel
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class SigLIP2Provider:
    name = "siglip2"
    dimension = 768

    def __init__(self) -> None:
        if not _AVAILABLE:
            raise ImportError(
                "Eksik bağımlılık: pip install transformers Pillow torch"
            )
        self._model = None
        self._processor = None

    def embed_image(self, image_url: str) -> Optional[np.ndarray]:
        
        try:
            image = self._fetch_image(image_url)
            return self._encode(image)
        except ImageFetchError as exc:
            logger.warning(
                "Görsel indirilemedi — metin embedding devam eder. "
                "provider=%s hata=%s", self.name, str(exc)
            )
            return None
        except Exception as exc:
            logger.warning(
                "SigLIP2 görsel embedding başarısız. "
                "provider=%s hata_tipi=%s", self.name, type(exc).__name__
            )
            return None

    def _fetch_image(self, url: str) -> "Image.Image":
       
        try:
            resp = requests.get(
                url,
                timeout=_TIMEOUT_SECONDS,
                max_redirects=_MAX_REDIRECTS,
                headers={"User-Agent": "PULSE/1.0"},
                stream=True,             # içerik boyutunu önce kontrol edebiliriz
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ImageFetchError(f"HTTP hatası: {type(exc).__name__}") from exc

        # Content-Type kontrolü
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
        if content_type not in _ALLOWED_CONTENT_TYPES:
            raise ImageFetchError(
                f"Desteklenmeyen görsel tipi: {content_type!r}. "
                f"Kabul edilenler: {_ALLOWED_CONTENT_TYPES}"
            )

        # Boyut kontrolü — stream ile chunk chunk okuyoruz
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=8192):
            total += len(chunk)
            if total > _MAX_IMAGE_BYTES:
                raise ImageFetchError(
                    f"Görsel dosyası çok büyük: >{_MAX_IMAGE_BYTES // (1024*1024)}MB"
                )
            chunks.append(chunk)

        try:
            return Image.open(BytesIO(b"".join(chunks))).convert("RGB")
        except Exception as exc:
            raise ImageFetchError(f"Görsel açılamadı: {type(exc).__name__}") from exc

    def _encode(self, image: "Image.Image") -> np.ndarray:
        processor, model = self._get_model()
        inputs = processor(images=image, return_tensors="pt")

        with torch.no_grad():
            features = model.get_image_features(**inputs)
            features = features / features.norm(dim=-1, keepdim=True)

        return features.squeeze().numpy().astype(np.float32)

    def _get_model(self):
        if self._model is None:
            logger.info("SigLIP2 yükleniyor")
            self._processor = AutoProcessor.from_pretrained(
                "google/siglip2-base-patch16-224"
            )
            self._model = AutoModel.from_pretrained(
                "google/siglip2-base-patch16-224"
            )
            self._model.eval()
        return self._processor, self._model