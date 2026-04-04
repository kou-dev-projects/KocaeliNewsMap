from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from app.db.database import db
from app.services.mcp.write_service import merge_duplicate_source_record_docs
from app.utils.content_hash import compute_duplicate_hash


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge duplicate source_records into a single canonical active record."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def _dedupe_hash(doc: dict[str, Any]) -> str:
    return str(
        doc.get("dedupe_hash")
        or compute_duplicate_hash(
            title=str(doc.get("title") or ""),
            summary=str(doc.get("summary") or ""),
            body=str(doc.get("body") or ""),
        )
    )


def _status_rank(status: str | None) -> int:
    return {
        "resolved": 4,
        "approximate": 3,
        "pending": 2,
        "failed": 1,
        "not_needed": 0,
    }.get(str(status or "").strip(), -1)


def _canonical_sort_key(doc: dict[str, Any]) -> tuple[int, int, int, int, float]:
    published_at = doc.get("published_at")
    published_ts = (
        published_at.timestamp()
        if isinstance(published_at, datetime)
        else 0.0
    )
    return (
        _status_rank(doc.get("geocode_status")),
        1 if doc.get("category_predicted") not in {None, "", "unknown"} else 0,
        len(doc.get("kaynak_listesi") or []),
        len(str(doc.get("body") or "")),
        published_ts,
    )


def main() -> None:
    args = _parse_args()
    source_records = db["source_records"]
    query: dict[str, Any] = {"record_status": {"$ne": "merged_duplicate"}}
    docs = list(source_records.find(query))
    if args.limit > 0:
        docs = docs[: args.limit]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for doc in docs:
        dedupe_hash = _dedupe_hash(doc)
        grouped[dedupe_hash].append(doc)

    summary = Counter()
    now = datetime.now(timezone.utc)

    for dedupe_hash, group in grouped.items():
        if len(group) < 2:
            doc = group[0]
            if doc.get("dedupe_hash") == dedupe_hash:
                continue
            if not args.dry_run:
                source_records.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"dedupe_hash": dedupe_hash, "updated_at": now}},
                )
                summary["hashed_singletons"] += 1
            continue

        ordered = sorted(group, key=_canonical_sort_key, reverse=True)
        canonical = ordered[0]
        summary["groups"] += 1
        summary["duplicates"] += len(ordered) - 1

        canonical_update: dict[str, Any] = {
            "dedupe_hash": dedupe_hash,
            "record_status": "active",
            "updated_at": now,
        }
        for duplicate in ordered[1:]:
            canonical_state = {**canonical, **canonical_update}
            canonical_update.update(
                merge_duplicate_source_record_docs(canonical_state, duplicate)
            )
            canonical_update["dedupe_hash"] = dedupe_hash
            canonical_update["record_status"] = "active"

            if not args.dry_run:
                source_records.update_one(
                    {"_id": duplicate["_id"]},
                    {
                        "$set": {
                            "record_status": "merged_duplicate",
                            "duplicate_of_record_id": canonical["_id"],
                            "dedupe_hash": dedupe_hash,
                            "updated_at": now,
                        }
                    },
                )
                summary["merged_records"] += 1

        if not args.dry_run:
            source_records.update_one(
                {"_id": canonical["_id"]},
                {"$set": canonical_update},
            )
            summary["updated_canonicals"] += 1

    print(
        {
            "dry_run": args.dry_run,
            "scanned": len(docs),
            "summary": dict(summary),
        }
    )


if __name__ == "__main__":
    main()
