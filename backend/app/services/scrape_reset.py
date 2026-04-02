from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


SCRAPED_DATA_COLLECTIONS: tuple[str, ...] = (
    "raw_documents",
    "source_records",
    "crawl_sessions",
)


@dataclass(frozen=True)
class ScrapeResetResult:
    deleted_counts: dict[str, int]

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
