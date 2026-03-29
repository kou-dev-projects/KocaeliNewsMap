from __future__ import annotations
import hashlib
import numpy as np


def _hash_to_vector(seed: str, dim: int) -> np.ndarray:
    
    values: list[float] = []
    digest = hashlib.sha256(seed.encode("utf-8")).digest()

    while len(values) < dim:
        for byte in digest:
            values.append((byte / 127.5) - 1.0)   # [-1.0, 1.0]
            if len(values) == dim:
                break
        digest = hashlib.sha256(digest).digest()   # zincir hash

    vec = np.array(values[:dim], dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec          # L2 normalize


class MockTextProvider:
    name = "mock-text"
    dimension = 1024

    def embed_text(self, text: str) -> np.ndarray:
        return _hash_to_vector(f"text:{text}", self.dimension)


class MockImageProvider:
    name = "mock-image"
    dimension = 768

    def embed_image(self, image_url: str) -> np.ndarray | None:
        if not image_url:
            return None
        return _hash_to_vector(f"image:{image_url}", self.dimension)