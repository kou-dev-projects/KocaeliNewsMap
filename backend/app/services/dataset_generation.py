from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any
from uuid import uuid4


logger = logging.getLogger(__name__)

_STATE_COLLECTION = "dataset_state"
_STATE_ID = "news_feed"
_MIGRATIONS_ATTEMPTED = False


@dataclass(frozen=True)
class DatasetGenerationState:
    active_generation: str | None
    pending_refresh_generation: str | None


def ensure_dataset_generation_support(database: Any) -> None:
    global _MIGRATIONS_ATTEMPTED
    if _MIGRATIONS_ATTEMPTED:
        return

    _MIGRATIONS_ATTEMPTED = True

    try:
        raw_documents = database["raw_documents"]
        source_records = database["source_records"]
        crawl_sessions = database["crawl_sessions"]
    except Exception:
        return

    try:
        raw_indexes = raw_documents.index_information()
        if "source_canonical_url_unique" in raw_indexes:
            raw_documents.drop_index("source_canonical_url_unique")

        raw_documents.create_index(
            [("source_id", 1), ("canonical_url", 1), ("dataset_generation", 1)],
            name="source_canonical_url_generation_unique",
            unique=True,
        )
        raw_documents.create_index(
            [("dataset_generation", 1), ("crawl_session_id", 1)],
            name="dataset_generation_crawl_session",
        )
        source_records.create_index(
            [("dataset_generation", 1), ("published_at", -1)],
            name="dataset_generation_published_at",
            sparse=True,
        )
        source_records.create_index(
            [
                ("dataset_generation", 1),
                ("category_predicted", 1),
                ("district_predicted", 1),
                ("published_at", -1),
            ],
            name="dataset_generation_category_district_published_at",
            sparse=True,
        )
        crawl_sessions.create_index(
            [("dataset_generation", 1), ("started_at", -1)],
            name="dataset_generation_started_at",
            sparse=True,
        )
    except Exception as exc:
        logger.warning(
            "dataset_generation.migrations_failed",
            extra={"error": f"{type(exc).__name__}: {exc}"},
        )


def _normalize_generation(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def get_dataset_generation_state(database: Any) -> DatasetGenerationState:
    try:
        document = database[_STATE_COLLECTION].find_one({"_id": _STATE_ID}) or {}
    except Exception:
        document = {}
    return DatasetGenerationState(
        active_generation=_normalize_generation(document.get("active_generation")),
        pending_refresh_generation=_normalize_generation(
            document.get("pending_refresh_generation")
        ),
    )


def resolve_visible_generation_query(database: Any) -> dict[str, Any]:
    state = get_dataset_generation_state(database)
    if state.active_generation:
        return {"dataset_generation": state.active_generation}
    if state.pending_refresh_generation:
        return {
            "$or": [
                {"dataset_generation": {"$exists": False}},
                {"dataset_generation": None},
            ]
        }
    return {}


def resolve_write_generation(
    database: Any,
    *,
    requested_generation: str | None = None,
) -> str | None:
    normalized_requested = _normalize_generation(requested_generation)
    if normalized_requested:
        return normalized_requested
    return get_dataset_generation_state(database).active_generation


def begin_refresh_generation(database: Any) -> str:
    ensure_dataset_generation_support(database)

    generation = uuid4().hex
    now = datetime.now(timezone.utc)
    database[_STATE_COLLECTION].update_one(
        {"_id": _STATE_ID},
        {
            "$set": {
                "pending_refresh_generation": generation,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    return generation


def activate_generation(database: Any, generation: str) -> None:
    normalized_generation = _normalize_generation(generation)
    if normalized_generation is None:
        raise ValueError("missing_dataset_generation")

    now = datetime.now(timezone.utc)
    database[_STATE_COLLECTION].update_one(
        {"_id": _STATE_ID},
        {
            "$set": {
                "active_generation": normalized_generation,
                "updated_at": now,
            },
            "$unset": {"pending_refresh_generation": ""},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


def clear_pending_refresh_generation(
    database: Any,
    *,
    expected_generation: str | None = None,
) -> None:
    query: dict[str, Any] = {"_id": _STATE_ID}
    normalized_expected = _normalize_generation(expected_generation)
    if normalized_expected:
        query["pending_refresh_generation"] = normalized_expected

    database[_STATE_COLLECTION].update_one(
        query,
        {
            "$unset": {"pending_refresh_generation": ""},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
