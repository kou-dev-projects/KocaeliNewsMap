from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


class CrawlSessionStore:
    def __init__(self, database=None) -> None:
        if database is None:
            from app.db.database import db as default_db

            self._db = default_db
        else:
            self._db = database

    def create_for_source(
        self,
        *,
        source_id,
        trigger_type: str,
        lookback_days: int,
        worker_version: str,
        trace_id: str,
        dataset_generation: str | None = None,
    ):
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=lookback_days)
        document = {
            "source_id": source_id,
            "trigger_type": trigger_type,
            "scope": "single_source",
            "lookback_days": lookback_days,
            "requested_window_start": window_start,
            "requested_window_end": now,
            "status": "running",
            "started_at": now,
            "fetched_count": 0,
            "parsed_count": 0,
            "failed_count": 0,
            "error_summary": [],
            "worker_version": worker_version,
            "trace_id": trace_id,
            "created_at": now,
            "updated_at": now,
        }
        if dataset_generation:
            document["dataset_generation"] = dataset_generation
        result = self._db["crawl_sessions"].insert_one(document)
        return result.inserted_id

    def finalize(
        self,
        *,
        session_id,
        fetched_count: int,
        parsed_count: int,
        failed_count: int,
        error_summary: list[dict[str, Any]],
    ) -> str:
        ended_at = datetime.now(timezone.utc)
        status = self._derive_status(
            parsed_count=parsed_count,
            failed_count=failed_count,
            error_summary=error_summary,
        )
        self._db["crawl_sessions"].update_one(
            {"_id": session_id},
            {
                "$set": {
                    "status": status,
                    "ended_at": ended_at,
                    "fetched_count": fetched_count,
                    "parsed_count": parsed_count,
                    "failed_count": failed_count,
                    "error_summary": error_summary,
                    "updated_at": ended_at,
                }
            },
        )
        return status

    @staticmethod
    def _derive_status(
        *,
        parsed_count: int,
        failed_count: int,
        error_summary: list[dict[str, Any]],
    ) -> str:
        if failed_count == 0 and not error_summary:
            return "success"
        if parsed_count > 0:
            return "partial"
        return "failed"


__all__ = ["CrawlSessionStore"]
