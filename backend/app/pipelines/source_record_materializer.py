from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.domain.enums import NewsCategory, normalize_kocaeli_district, normalize_news_category
from app.scrapers.base.date_utils import parse_published_at_raw
from app.services.classifier.factory import build_classifier_service
from app.services.classifier.schemas import ClassificationInput, ClassificationResult
from app.services.ner.factory import build_ner_service
from app.services.ner.schemas import NERInput, NERResult
from app.utils.content_hash import compute_content_hash


logger = logging.getLogger(__name__)


@dataclass
class SourceRecordMaterializer:
    classifier_service: Any | None = None
    ner_service: Any | None = None

    def __post_init__(self) -> None:
        if self.classifier_service is None:
            try:
                self.classifier_service = build_classifier_service()
            except Exception as exc:
                logger.warning(
                    "pipeline.materializer.classifier_unavailable",
                    extra={"error": f"{type(exc).__name__}: {exc}"},
                )
                self.classifier_service = None
        if self.ner_service is None:
            try:
                self.ner_service = build_ner_service()
            except Exception as exc:
                logger.warning(
                    "pipeline.materializer.ner_unavailable",
                    extra={"error": f"{type(exc).__name__}: {exc}"},
                )
                self.ner_service = None

    def materialize(
        self,
        *,
        raw_document: dict[str, Any],
        source_document: dict[str, Any],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current_time = now or datetime.now(timezone.utc)
        title = raw_document.get("title_raw", "")
        body = raw_document.get("content_raw") or raw_document.get("text_raw") or ""
        summary = self._build_summary(body)

        classification = self._classify(
            title=title,
            summary=summary,
            body=body,
        )
        ner_result = self._extract_locations(
            title=title,
            summary=summary,
            body=body,
        )

        district, district_confidence, location_text = self._extract_location_fields(ner_result)
        geocode_status = "pending" if location_text or district else "not_needed"
        category = normalize_news_category(classification.category.value)

        record = {
            "raw_document_id": raw_document["_id"],
            "source_id": source_document["_id"],
            "canonical_url": raw_document["canonical_url"],
            "title": title,
            "body": body,
            "published_at": self._normalize_published_at(
                raw_document.get("published_at_raw"),
                raw_document.get("scraped_at"),
                current_time,
            ),
            "detected_language": raw_document.get("language") or "tr",
            "category_predicted": (category or classification.category).value,
            "category_confidence": classification.confidence,
            "category_model_version": classification.method,
            "district_predicted": district,
            "location_text_extracted": location_text,
            "geocode_status": geocode_status,
            "text_hash": self._text_hash(title=title, body=body),
            "source_name_snapshot": source_document.get("display_name", raw_document.get("domain", "")),
            "source_url_snapshot": source_document.get("base_url", raw_document.get("resolved_url", raw_document["canonical_url"])),
            "kaynak_listesi": [raw_document.get("domain", "")],
            "pipeline_status": "classified",
            "record_status": "active",
            "schema_version": "1.0",
            "updated_at": current_time,
        }

        if summary:
            record["summary"] = summary
        if district_confidence is not None:
            record["district_confidence"] = district_confidence

        return record

    def _classify(self, *, title: str, summary: Optional[str], body: str) -> ClassificationResult:
        if self.classifier_service is None:
            return self._fallback_classification()

        try:
            return self.classifier_service.classify(
                ClassificationInput(
                    title=title,
                    summary=summary,
                    content=body,
                )
            )
        except Exception as exc:
            logger.warning(
                "pipeline.materializer.classification_failed",
                extra={"error": f"{type(exc).__name__}: {exc}"},
            )
            return self._fallback_classification()

    def _extract_locations(self, *, title: str, summary: Optional[str], body: str) -> NERResult:
        if self.ner_service is None:
            return self._fallback_ner_result()

        try:
            return self.ner_service.extract_locations(
                NERInput(
                    title=title,
                    summary=summary,
                    content=body,
                )
            )
        except Exception as exc:
            logger.warning(
                "pipeline.materializer.ner_failed",
                extra={"error": f"{type(exc).__name__}: {exc}"},
            )
            return self._fallback_ner_result()

    def _extract_location_fields(self, ner_result: Any) -> tuple[Optional[str], Optional[float], Optional[str]]:
        district = None
        if ner_result.validated_districts:
            district_enum = normalize_kocaeli_district(ner_result.validated_districts[0])
            district = district_enum.value if district_enum else None
        location_text = ner_result.location_candidates[0].original_text if ner_result.location_candidates else None

        district_confidence = None
        if district:
            for candidate in ner_result.location_candidates:
                candidate_district = normalize_kocaeli_district(candidate.district)
                if candidate_district and candidate_district.value == district:
                    district_confidence = candidate.score
                    break

        return district, district_confidence, location_text

    def _build_summary(self, body: str) -> Optional[str]:
        text = (body or "").strip()
        if not text:
            return None
        summary = text[:280].strip()
        return summary if summary else None

    def _text_hash(self, *, title: str, body: str) -> str:
        return compute_content_hash(title=title, body=body)

    def _normalize_published_at(
        self,
        published_at_raw: Any,
        scraped_at: Any,
        fallback: datetime,
    ) -> datetime:
        if isinstance(published_at_raw, datetime):
            return published_at_raw
        if isinstance(published_at_raw, str):
            parsed = parse_published_at_raw(published_at_raw)
            if parsed:
                return parsed

        if isinstance(scraped_at, datetime):
            return scraped_at
        if isinstance(scraped_at, str):
            parsed = parse_published_at_raw(scraped_at)
            if parsed:
                return parsed

        return fallback

    def _fallback_classification(self) -> ClassificationResult:
        return ClassificationResult(
            category=NewsCategory.UNKNOWN,
            confidence=0.0,
            method="fallback_unknown",
        )

    def _fallback_ner_result(self) -> NERResult:
        return NERResult(
            raw_entities=[],
            location_candidates=[],
            validated_districts=[],
            provider="fallback_none",
        )
