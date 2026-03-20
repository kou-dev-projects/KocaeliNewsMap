from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EmbeddingInput:
    """
    Immutable input. frozen=True:
    - Embedding sırasında değiştirilemez
    - Hash'lenebilir → ileride cache key olarak kullanılabilir
    """
    title: str
    source: str                   # kaynak domain — zorunlu, log'da görünür
    summary: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None   # str — HttpUrl değil (Kocaeli URL'leri sorunlu)

    def build_text_payload(self) -> str:
        """Embedding'e girecek ham metin. BGE-M3 8192 token destekler."""
        parts = [self.title]
        if self.summary:
            parts.append(self.summary)
        if self.content:
            parts.append(self.content[:4000])   # ~1000 token, haber için yeterli
        return "\n".join(p.strip() for p in parts if p.strip())

    def safe_log_repr(self) -> dict:
        """Log'a yazılacak temsil — URL veya gizli alan içermez."""
        return {
            "title_len": len(self.title),
            "has_summary": bool(self.summary),
            "has_content": bool(self.content),
            "has_image": bool(self.image_url),
            "source": self.source,
        }


@dataclass(frozen=True)
class TextEmbedding:
    """BGE-M3 çıktısı — 1024-dim. MongoDB'de text_embedding alanına yazılır."""
    vector: list[float]
    dimension: int
    provider: str


@dataclass(frozen=True)
class ImageEmbedding:
    """SigLIP2 çıktısı — 768-dim. MongoDB'de image_embedding alanına yazılır."""
    vector: list[float]
    dimension: int
    provider: str


@dataclass(frozen=True)
class DuplicateScore:
    
    text_similarity: float
    image_similarity: Optional[float]     # görsel yoksa None
    final_score: float
    is_duplicate: bool
    matched_news_id: Optional[str] = None
    merged_kaynak_listesi: Optional[list[str]] = None
    debug: Optional[dict] = None          # yapılandırılmış metrik — reason yerine