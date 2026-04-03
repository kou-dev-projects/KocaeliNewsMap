from __future__ import annotations

import argparse
from collections import Counter

from app.db.database import db
from app.pipelines import SourceRecordMaterializer
from app.pipelines.location_versions import (
    GAZETTEER_VERSION,
    LOCATION_PIPELINE_VERSION,
    LOGICAL_LOCATION_CATALOG_VERSION,
)
from app.services.geocoding.provider_versions import PROVIDER_VERSIONS

_TRACKED_OPTIONAL_FIELDS = (
    "geocode_point",
    "geocode_bbox",
    "geocode_provider",
    "geocode_provider_version",
    "location_resolution_method",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recompute source_records with the current materialization pipeline."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum records to reprocess.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only compute the new result without writing it back to MongoDB.",
    )
    parser.add_argument(
        "--mode",
        choices=("stale-version", "district-fallback", "missing-point", "all"),
        default="stale-version",
        help="Select which records should be recomputed.",
    )
    return parser.parse_args()


def _build_query(mode: str) -> dict[str, object]:
    if mode == "stale-version":
        provider_version_branches = []
        for provider, version in PROVIDER_VERSIONS.items():
            provider_version_branches.extend(
                [
                    {
                        "geocode_provider": provider,
                        "geocode_provider_version": {"$exists": False},
                    },
                    {
                        "geocode_provider": provider,
                        "geocode_provider_version": {"$ne": version},
                    },
                ]
            )

        return {
            "$or": [
                {"location_pipeline_version": {"$exists": False}},
                {"location_pipeline_version": {"$ne": LOCATION_PIPELINE_VERSION}},
                {"gazetteer_version": {"$exists": False}},
                {"gazetteer_version": {"$ne": GAZETTEER_VERSION}},
                {"logical_catalog_version": {"$exists": False}},
                {"logical_catalog_version": {"$ne": LOGICAL_LOCATION_CATALOG_VERSION}},
                *provider_version_branches,
            ]
        }
    if mode == "district-fallback":
        return {
            "geocode_provider": "district_fallback",
            "geocode_point": {"$ne": None},
        }
    if mode == "missing-point":
        return {"geocode_point": None}
    return {}


def main() -> None:
    args = _parse_args()

    source_records = db["source_records"]
    raw_documents = db["raw_documents"]
    sources = db["sources"]
    materializer = SourceRecordMaterializer()

    query = _build_query(args.mode)
    cursor = source_records.find(query).sort("updated_at", -1)
    if args.limit > 0:
        cursor = cursor.limit(args.limit)

    summary = Counter()
    status_counts = Counter()

    for record in cursor:
        summary["scanned"] += 1

        raw_document = raw_documents.find_one({"_id": record["raw_document_id"]})
        source_document = sources.find_one({"_id": record["source_id"]})
        if raw_document is None or source_document is None:
            summary["skipped_missing_dependencies"] += 1
            continue

        refreshed_record = materializer.materialize(
            raw_document=raw_document,
            source_document=source_document,
        )
        status_counts[refreshed_record["geocode_status"]] += 1

        if args.dry_run:
            continue

        update_document = {
            "$set": {
                key: value
                for key, value in refreshed_record.items()
                if key != "created_at"
            }
        }
        unset_fields = {
            field: ""
            for field in _TRACKED_OPTIONAL_FIELDS
            if field not in refreshed_record
        }
        if unset_fields:
            update_document["$unset"] = unset_fields

        source_records.update_one({"_id": record["_id"]}, update_document)
        summary["updated"] += 1

    print(
        {
            "dry_run": args.dry_run,
            "mode": args.mode,
            "summary": dict(summary),
            "geocode_status_counts": dict(status_counts),
        }
    )


if __name__ == "__main__":
    main()
