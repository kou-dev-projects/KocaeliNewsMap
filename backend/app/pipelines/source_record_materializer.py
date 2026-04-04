from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.domain.enums import NewsCategory, normalize_kocaeli_district, normalize_news_category
from app.scrapers.base.date_utils import parse_published_at_raw
from app.services.classifier.factory import build_classifier_service
from app.services.classifier.schemas import ClassificationInput, ClassificationResult
from app.services.geocoding.factory import build_geocoding_service
from app.services.geocoding.schemas import GeocodingFailure, GeocodingResult
from app.services.geocoding.service import (
    build_geocoding_inputs_from_ner,
    is_district_level_geocoding_input,
)
from app.services.logical_location import build_logical_location_candidates
from app.services.ner.factory import build_ner_service
from app.services.ner.schemas import NERInput, NERResult
from app.utils.content_cleaning import clean_news_text
from app.utils.content_hash import compute_content_hash

from .location_versions import (
    GAZETTEER_VERSION,
    LIVE_LOCATION_BENCHMARK_VERSION,
    LOCATION_PIPELINE_VERSION,
    LOGICAL_LOCATION_CATALOG_VERSION,
    SOURCE_RECORD_SCHEMA_VERSION,
)


logger = logging.getLogger(__name__)


@dataclass
class SourceRecordMaterializer:
    classifier_service: Any | None = None
    ner_service: Any | None = None
    geocoding_service: Any | None = None

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
        if self.geocoding_service is None:
            try:
                self.geocoding_service = build_geocoding_service()
            except Exception as exc:
                logger.warning(
                    "pipeline.materializer.geocoding_unavailable",
                    extra={"error": f"{type(exc).__name__}: {exc}"},
                )
                self.geocoding_service = None

    def materialize(
        self,
        *,
        raw_document: dict[str, Any],
        source_document: dict[str, Any],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current_time = now or datetime.now(timezone.utc)
        title = raw_document.get("title_raw", "")
        body = clean_news_text(
            raw_document.get("content_raw") or raw_document.get("text_raw") or ""
        ) or ""
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

        district, district_confidence, location_text = self._extract_location_fields(
            ner_result
        )
        geocode_data = self._resolve_geocoding(
            title=title,
            summary=summary,
            body=body,
            classification=classification,
            ner_result=ner_result,
            fallback_district=district,
            news_id=(
                str(raw_document.get("_id"))
                if raw_document.get("_id") is not None
                else None
            ),
        )
        district = geocode_data["district_predicted"] or district
        location_text = geocode_data["location_text_extracted"] or location_text
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
            "geocode_status": geocode_data["geocode_status"],
            "location_pipeline_version": LOCATION_PIPELINE_VERSION,
            "gazetteer_version": GAZETTEER_VERSION,
            "logical_catalog_version": LOGICAL_LOCATION_CATALOG_VERSION,
            "location_benchmark_version": LIVE_LOCATION_BENCHMARK_VERSION,
            "text_hash": self._text_hash(title=title, body=body),
            "source_name_snapshot": source_document.get("display_name", raw_document.get("domain", "")),
            "source_url_snapshot": source_document.get("base_url", raw_document.get("resolved_url", raw_document["canonical_url"])),
            "kaynak_listesi": [raw_document.get("domain", "")],
            "pipeline_status": geocode_data["pipeline_status"],
            "record_status": "active",
            "schema_version": SOURCE_RECORD_SCHEMA_VERSION,
            "updated_at": current_time,
        }

        if summary:
            record["summary"] = summary
        if district_confidence is not None:
            record["district_confidence"] = district_confidence
        if geocode_data["geocode_provider"] is not None:
            record["geocode_provider"] = geocode_data["geocode_provider"]
        if geocode_data["geocode_provider_version"] is not None:
            record["geocode_provider_version"] = geocode_data[
                "geocode_provider_version"
            ]
        if geocode_data["location_resolution_method"] is not None:
            record["location_resolution_method"] = geocode_data[
                "location_resolution_method"
            ]
        if geocode_data["geocode_point"] is not None:
            record["geocode_point"] = geocode_data["geocode_point"]
        if geocode_data["geocode_bbox"] is not None:
            record["geocode_bbox"] = geocode_data["geocode_bbox"]

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

    def _extract_location_fields(
        self,
        ner_result: Any,
    ) -> tuple[Optional[str], Optional[float], Optional[str]]:
        district = None
        district_confidence = None
        for candidate in ner_result.location_candidates:
            candidate_district = normalize_kocaeli_district(candidate.district)
            if candidate_district is None:
                continue
            district = candidate_district.value
            district_confidence = candidate.score
            break

        if district is None and ner_result.validated_districts:
            district_enum = normalize_kocaeli_district(
                ner_result.validated_districts[0]
            )
            district = district_enum.value if district_enum else None

        location_text = None
        for candidate in ner_result.location_candidates:
            candidate_text = (candidate.original_text or "").strip()
            if not candidate_text:
                continue
            if self._is_generic_location_text(candidate_text):
                continue
            if (
                candidate.district
                or candidate.neighborhood
                or candidate.is_kocaeli_district
                or self._looks_like_precise_location(candidate_text)
            ):
                location_text = candidate_text
                break

        if district and district_confidence is None:
            for candidate in ner_result.location_candidates:
                candidate_district = normalize_kocaeli_district(candidate.district)
                if candidate_district and candidate_district.value == district:
                    district_confidence = candidate.score
                    break

        return district, district_confidence, location_text

    def _resolve_geocoding(
        self,
        *,
        title: str,
        summary: Optional[str],
        body: str,
        classification: ClassificationResult,
        ner_result: NERResult,
        fallback_district: Optional[str],
        news_id: Optional[str],
    ) -> dict[str, Any]:
        logical_candidates = build_logical_location_candidates(
            title=title,
            summary=summary,
            body=body,
            classification=classification,
            ner_result=ner_result,
            fallback_district=fallback_district,
        )
        geocoding_inputs = build_geocoding_inputs_from_ner(ner_result, news_id=news_id)

        attempts: list[tuple[Any, Optional[Any]]] = []
        seen_inputs: set[tuple[str, str | None, str | None]] = set()

        def add_attempt(geocoding_input: Any, logical_candidate: Any | None = None) -> None:
            key = (
                geocoding_input.address.casefold(),
                geocoding_input.district_hint.casefold()
                if geocoding_input.district_hint
                else None,
                geocoding_input.neighborhood.casefold()
                if geocoding_input.neighborhood
                else None,
            )
            if key in seen_inputs:
                return
            seen_inputs.add(key)
            attempts.append((geocoding_input, logical_candidate))

        for candidate in logical_candidates:
            add_attempt(candidate.to_geocoding_input(news_id=news_id), candidate)
        for geocoding_input in geocoding_inputs:
            add_attempt(geocoding_input)

        if not attempts:
            return {
                "geocode_status": "not_needed",
                "pipeline_status": "geocoded",
                "geocode_provider": None,
                "geocode_provider_version": None,
                "geocode_point": None,
                "geocode_bbox": None,
                "district_predicted": fallback_district,
                "location_text_extracted": None,
                "location_resolution_method": None,
            }

        if self.geocoding_service is None:
            return {
                "geocode_status": "pending",
                "pipeline_status": "classified",
                "geocode_provider": None,
                "geocode_provider_version": None,
                "geocode_point": None,
                "geocode_bbox": None,
                "district_predicted": fallback_district,
                "location_text_extracted": None,
                "location_resolution_method": None,
            }

        failures: list[GeocodingFailure] = []
        for geocoding_input, logical_candidate in attempts:
            try:
                result = self.geocoding_service.geocode(geocoding_input)
            except Exception as exc:
                logger.warning(
                    "pipeline.materializer.geocoding_failed",
                    extra={"error": f"{type(exc).__name__}: {exc}"},
                )
                return {
                    "geocode_status": "pending",
                    "pipeline_status": "classified",
                    "geocode_provider": None,
                    "geocode_provider_version": None,
                    "geocode_point": None,
                    "geocode_bbox": None,
                    "district_predicted": fallback_district,
                    "location_text_extracted": None,
                    "location_resolution_method": None,
                }

            if isinstance(result, GeocodingFailure):
                failures.append(result)
                continue

            resolved_district = fallback_district
            if not resolved_district and result.district:
                district_enum = normalize_kocaeli_district(result.district)
                resolved_district = district_enum.value if district_enum else None

            return {
                "geocode_status": self._geocode_status_from_result(
                    result,
                    geocoding_input=geocoding_input,
                    logical_candidate=logical_candidate,
                ),
                "pipeline_status": "geocoded",
                "geocode_provider": result.source,
                "geocode_provider_version": result.provider_version,
                "geocode_point": {
                    "type": "Point",
                    "coordinates": [result.lng, result.lat],
                },
                "geocode_bbox": None,
                "district_predicted": resolved_district,
                "location_text_extracted": (
                    logical_candidate.location_text
                    if logical_candidate
                    else geocoding_input.address
                ),
                "location_resolution_method": (
                    logical_candidate.strategy if logical_candidate else None
                ),
            }

        if any(
            failure.failure_type in {"rate_limit", "queue_full"}
            for failure in failures
        ):
            return {
                "geocode_status": "pending",
                "pipeline_status": "classified",
                "geocode_provider": None,
                "geocode_provider_version": None,
                "geocode_point": None,
                "geocode_bbox": None,
                "district_predicted": fallback_district,
                "location_text_extracted": None,
                "location_resolution_method": None,
            }

        if fallback_district is not None:
            return {
                "geocode_status": "approximate",
                "pipeline_status": "geocoded",
                "geocode_provider": "district_fallback",
                "geocode_provider_version": None,
                "geocode_point": None,
                "geocode_bbox": None,
                "district_predicted": fallback_district,
                "location_text_extracted": None,
                "location_resolution_method": None,
            }

        return {
            "geocode_status": "failed",
            "pipeline_status": "geocoded",
            "geocode_provider": None,
            "geocode_provider_version": None,
            "geocode_point": None,
            "geocode_bbox": None,
            "district_predicted": fallback_district,
            "location_text_extracted": None,
            "location_resolution_method": None,
        }

    def _geocode_status_from_result(
        self,
        result: GeocodingResult,
        *,
        geocoding_input: Any,
        logical_candidate: Any | None = None,
    ) -> str:
        if logical_candidate is not None:
            return logical_candidate.geocode_status
        if is_district_level_geocoding_input(geocoding_input):
            return "approximate"
        if result.confidence < 0.75:
            return "approximate"
        return "resolved"

    @staticmethod
    def _looks_like_precise_location(value: str) -> bool:
        normalized = value.casefold()
        return any(
            token in normalized
            for token in (
                "mahallesi",
                "mahalle",
                "sokak",
                "cadde",
                "bulvar",
                "baraji",
                "goleti",
                "tesisi",
                "stadyumu",
                "otoyolu",
                "terminali",
            )
        )

    @staticmethod
    def _is_generic_location_text(value: str) -> bool:
        return value.casefold() in {
            "belediyesi",
            "belediye",
            "buyuksehir belediyesi",
            "valilik",
            "kaymakamligi",
            "mudurlugu",
            "genel mudurlugu",
            "bakanligi",
        }

    def _build_summary(self, body: str) -> Optional[str]:
        text = clean_news_text(body or "")
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
