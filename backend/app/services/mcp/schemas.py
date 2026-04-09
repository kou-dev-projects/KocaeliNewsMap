from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import hashlib

class WriteStatus(str, Enum):
    INSERTED = "inserted"
    DUPLICATE_MERGED = "duplicate_merged"
    QUEUED = "queued"           # write service geçici down — queue'ya alındı
    DEAD_LETTERED = "dead_lettered"  # max retry aşıldı


@dataclass(frozen=True)
class NewsWriteRequest:
    title: str
    url: str
    source: str                    # kaynak domain
    content: Optional[str] = None
    summary: Optional[str] = None
    published_at: Optional[str] = None
    raw_html: Optional[str] = None
    crawl_session_id: Optional[str] = None
    dataset_generation: Optional[str] = None
    resolved_url: Optional[str] = None
    scraped_at: Optional[str] = None
    parser_version: str = "mcp_write_v1"

    def idempotency_key(self) -> str:
        payload = f"{self.source}::{self.url}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def safe_log_repr(self) -> dict:
        return {
            "title_len": len(self.title),
            "source": self.source,
            "url_hash": self.idempotency_key()[:16],
            "dataset_generation": self.dataset_generation,
        }


@dataclass(frozen=True)
class WriteResult:
 
    status: WriteStatus
    news_id: Optional[str]
    was_duplicate: bool
    idempotency_key: str
    reason: Optional[str] = None

@dataclass
class LeaseInfo:
   
    source: str
    worker_id: str
    expires_at: datetime
    ttl_seconds: int

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
