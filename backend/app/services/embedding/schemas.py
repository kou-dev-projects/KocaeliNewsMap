from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EmbeddingInput:
  
    title: str
    source: str                   # kaynak domain — zorunlu, log'da görünür
    summary: Optional[str] = None
    content: Optional[str] = None

    def build_text_payload(self) -> str:
        
        parts = [self.title]
        if self.summary:
            parts.append(self.summary)
        if self.content:
            parts.append(self.content[:4000])   # ~1000 token, haber için yeterli
        return "\n".join(p.strip() for p in parts if p.strip())

    def safe_log_repr(self) -> dict:
        return {
            "title_len": len(self.title),
            "has_summary": bool(self.summary),
            "has_content": bool(self.content),
            "source": self.source,
        }


@dataclass(frozen=True)
class TextEmbedding:
    vector: list[float]
    dimension: int
    provider: str


@dataclass(frozen=True)
class DuplicateScore:
    
    text_similarity: float
    final_score: float
    is_duplicate: bool
    matched_news_id: Optional[str] = None
    merged_kaynak_listesi: Optional[list[str]] = None
    debug: Optional[dict] = None          # yapılandırılmış metrik — reason yerine