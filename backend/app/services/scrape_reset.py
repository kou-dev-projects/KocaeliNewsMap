from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


SCRAPED_DATA_COLLECTIONS: tuple[str, ...] = (
    "raw_documents",
    "source_records",
)


@dataclass(frozen=True)
class ScrapeResetResult:
    deleted_counts: dict[str, int]

    @property
    def total_deleted(self) -> int:
        return sum(self.deleted_counts.values())


@dataclass(frozen=True)
class ScrapeRefreshCleanupResult:
    deleted_counts: dict[str, int]
    generation: str
    mode: str

    @property
    def total_deleted(self) -> int:
        return sum(self.deleted_counts.values())


def reset_scraped_news_data(database: Any) -> ScrapeResetResult:
    deleted_counts: dict[str, int] = {}

    for collection_name in SCRAPED_DATA_COLLECTIONS:
        result = database[collection_name].delete_many({})
        deleted_counts[collection_name] = result.deleted_count

    logger.info(
        "scrape.reset.completed",
        extra={
            "collections": list(SCRAPED_DATA_COLLECTIONS),
            "deleted_counts": deleted_counts,
            "total_deleted": sum(deleted_counts.values()),
        },
    )

    return ScrapeResetResult(deleted_counts=deleted_counts)


def _delete_raw_and_source_records(
    database: Any,
    *,
    raw_document_query: dict[str, Any],
) -> dict[str, int]:
    stale_raw_document_ids = [
        document["_id"]
        for document in database["raw_documents"].find(
            raw_document_query,
            {"_id": 1},
        )
    ]

    deleted_counts = {
        "source_records": 0,
        "raw_documents": 0,
    }

    if not stale_raw_document_ids:
        return deleted_counts

    deleted_counts["source_records"] = database["source_records"].delete_many(
        {"raw_document_id": {"$in": stale_raw_document_ids}}
    ).deleted_count
    deleted_counts["raw_documents"] = database["raw_documents"].delete_many(
        {"_id": {"$in": stale_raw_document_ids}}
    ).deleted_count
    return deleted_counts


def cleanup_stale_refresh_data(
    database: Any,
    *,
    active_generation: str,
) -> ScrapeRefreshCleanupResult:
    normalized_generation = str(active_generation or "").strip()
    if not normalized_generation:
        raise ValueError("missing_active_generation")

    deleted_counts = _delete_raw_and_source_records(
        database,
        raw_document_query={"dataset_generation": {"$ne": normalized_generation}},
    )

    logger.info(
        "scrape.refresh_cleanup.completed",
        extra={
            "active_generation": normalized_generation,
            "deleted_counts": deleted_counts,
            "total_deleted": sum(deleted_counts.values()),
        },
    )

    return ScrapeRefreshCleanupResult(
        deleted_counts=deleted_counts,
        generation=normalized_generation,
        mode="activate",
    )


def cleanup_pending_refresh_data(
    database: Any,
    *,
    pending_generation: str,
) -> ScrapeRefreshCleanupResult:
    normalized_generation = str(pending_generation or "").strip()
    if not normalized_generation:
        raise ValueError("missing_pending_generation")

    deleted_counts = _delete_raw_and_source_records(
        database,
        raw_document_query={"dataset_generation": normalized_generation},
    )

    logger.info(
        "scrape.refresh_cleanup.discarded",
        extra={
            "pending_generation": normalized_generation,
            "deleted_counts": deleted_counts,
            "total_deleted": sum(deleted_counts.values()),
        },
    )

    return ScrapeRefreshCleanupResult(
        deleted_counts=deleted_counts,
        generation=normalized_generation,
        mode="discard",
    )
