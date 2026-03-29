from __future__ import annotations
import numpy as np


def cosine_similarity(
    a: list[float] | np.ndarray,
    b: list[float] | np.ndarray,
) -> float:
   
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)

    if va.shape != vb.shape:
        raise ValueError(
            f"Vektör boyutları uyuşmuyor: {va.shape} vs {vb.shape}"
        )

    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0   # sıfır vektör — similarity tanımsız, 0 dön

    return float(np.dot(va, vb) / (norm_a * norm_b))