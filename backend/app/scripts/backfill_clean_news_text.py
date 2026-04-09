from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.db.database import db
from app.services.classifier.factory import build_classifier_service
from app.services.classifier.schemas import ClassificationInput
from app.utils.content_cleaning import clean_news_text


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean stored source_records text fields and optionally reclassify them."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum records to scan.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the changes back to MongoDB.",
    )
    parser.add_argument(
        "--reclassify",
        action="store_true",
        help="Recompute category fields after cleaning text.",
    )
    return parser.parse_args()


def _cleaned_fields(record: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}

    for field in ("summary", "body"):
        original = record.get(field)
        cleaned = clean_news_text(original)
        if cleaned != original:
            updates[field] = cleaned

    return updates
def main() -> None:
    args = _parse_args()
    source_records = db["source_records"]
    cursor = source_records.find({}).sort("updated_at", -1)
    if args.limit > 0:
        cursor = cursor.limit(args.limit)

    summary = Counter()
    category_changes = Counter()

    classifier = build_classifier_service() if args.reclassify else None

    for record in cursor:
        summary["scanned"] += 1

        updates = _cleaned_fields(record)
        cleaned_record = dict(record)
        cleaned_record.update(updates)

        if classifier is not None:
            title = clean_news_text(cleaned_record.get("title") or "") or ""
            result = classifier.classify(
                ClassificationInput(
                    news_id=str(cleaned_record["_id"]),
                    title=title,
                    summary=cleaned_record.get("summary"),
                    content=cleaned_record.get("body"),
                )
            )
            if result is None:
                new_category = "unknown"
                new_confidence = 0.0
                new_method = "keyword_only"
            else:
                new_category = result.category.value
                new_confidence = result.confidence
                new_method = result.method

            old_category = cleaned_record.get("category_predicted") or "unknown"
            if old_category != new_category:
                category_changes[(old_category, new_category)] += 1
                updates["category_predicted"] = new_category
            if cleaned_record.get("category_confidence") != new_confidence:
                updates["category_confidence"] = new_confidence
            if cleaned_record.get("category_model_version") != new_method:
                updates["category_model_version"] = new_method

        if not updates:
            continue

        summary["changed"] += 1
        if "summary" in updates:
            summary["summary_cleaned"] += 1
        if "body" in updates:
            summary["body_cleaned"] += 1
        if "category_predicted" in updates:
            summary["reclassified"] += 1

        if not args.apply:
            continue

        updates["updated_at"] = datetime.now(timezone.utc)
        source_records.update_one({"_id": record["_id"]}, {"$set": updates})
        summary["updated"] += 1

    print(
        {
            "apply": args.apply,
            "reclassify": args.reclassify,
            "summary": dict(summary),
            "category_changes": {
                f"{old}->{new}": count
                for (old, new), count in category_changes.items()
            },
        }
    )


if __name__ == "__main__":
    main()
