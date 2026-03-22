from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NewsCategory(str, Enum):
   
    TRAFIK_KAZASI = "trafik_kazasi"
    YANGIN = "yangin"
    HIRSIZLIK = "hirsizlik"
    ELEKTRIK_KESINTISI = "elektrik_kesintisi"
    KULTUREL_ETKINLIK = "kulturel_etkinlik"
    UNKNOWN = "unknown"   


CATEGORY_PRIORITY: dict[NewsCategory, int] = {
    NewsCategory.TRAFIK_KAZASI:      1,   # en yüksek öncelik
    NewsCategory.YANGIN:             2,
    NewsCategory.HIRSIZLIK:          3,
    NewsCategory.ELEKTRIK_KESINTISI: 4,
    NewsCategory.KULTUREL_ETKINLIK:  5,
    NewsCategory.UNKNOWN:            99,
}


@dataclass(frozen=True)
class ClassificationInput:

    title: str
    news_id: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None

    def full_text(self) -> str:
       
        parts = [self.title]
        if self.summary:
            parts.append(self.summary)
        if self.content:
            parts.append(self.content[:1000])   # İlk 1000 karakter yeterli
        return " ".join(parts)


@dataclass(frozen=True)
class ClassificationResult:
    
    category: NewsCategory
    confidence: float
    method: str
    news_id: Optional[str] = None
    matched_keywords: list[str] = field(default_factory=list)
    all_scores: dict[str, float] = field(default_factory=dict)