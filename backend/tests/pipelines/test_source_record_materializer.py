from app.domain.enums import NewsCategory
from app.pipelines.source_record_materializer import SourceRecordMaterializer
from app.services.classifier.schemas import ClassificationResult
from app.services.geocoding.schemas import GeocodingFailure
from app.services.geocoding.schemas import GeocodingResult
from app.services.ner.schemas import LocationCandidate, NERResult


class ExplodingClassifier:
    def classify(self, input_data):
        raise RuntimeError("classifier unavailable")


class ExplodingNER:
    def extract_locations(self, input_data):
        raise RuntimeError("ner unavailable")


def test_materializer_falls_back_when_services_fail():
    materializer = SourceRecordMaterializer(
        classifier_service=ExplodingClassifier(),
        ner_service=ExplodingNER(),
        geocoding_service=object(),
    )

    record = materializer.materialize(
        raw_document={
            "_id": "raw_1",
            "source_id": "source_1",
            "canonical_url": "https://example.com/test",
            "title_raw": "Test baslik",
            "content_raw": "Test icerik",
            "text_raw": "Test icerik",
            "published_at_raw": None,
            "scraped_at": "2026-03-23T10:30:00+00:00",
            "language": "tr",
            "domain": "ozgurkocaeli.com.tr",
            "resolved_url": "https://example.com/test",
        },
        source_document={
            "_id": "source_1",
            "display_name": "Ozgur Kocaeli",
            "base_url": "https://www.ozgurkocaeli.com.tr",
        },
    )

    assert record["category_predicted"] == "unknown"
    assert record["category_confidence"] == 0.0
    assert record["category_model_version"] == "fallback_unknown"
    assert record["district_predicted"] is None
    assert record["location_text_extracted"] is None
    assert record["geocode_status"] == "not_needed"
    assert record["pipeline_status"] == "geocoded"


class FixedClassifier:
    def classify(self, input_data):
        return ClassificationResult(
            category=NewsCategory.YANGIN,
            confidence=0.94,
            method="fixed_classifier",
        )


class FixedNER:
    def extract_locations(self, input_data):
        return NERResult(
            raw_entities=[],
            location_candidates=[
                LocationCandidate(
                    original_text="Izmit",
                    normalized_text="izmit",
                    score=0.91,
                    is_kocaeli_district=True,
                    district="Izmit",
                )
            ],
            validated_districts=["Izmit"],
            provider="fixed_ner",
        )


class FixedGeocoder:
    def geocode(self, input_data):
        return GeocodingResult(
            address=input_data.address,
            lat=40.7654,
            lng=29.9408,
            display_name="Izmit, Kocaeli, Turkey",
            confidence=0.89,
            source="mock",
            provider_version="test",
            district="Izmit",
        )


class FailingGeocoder:
    def geocode(self, input_data):
        return GeocodingFailure(
            address=input_data.address,
            reason="Provider timeout",
            failure_type="provider_error",
            news_id=input_data.news_id,
        )


def test_materializer_persists_geocoding_fields_when_resolved():
    materializer = SourceRecordMaterializer(
        classifier_service=FixedClassifier(),
        ner_service=FixedNER(),
        geocoding_service=FixedGeocoder(),
    )

    record = materializer.materialize(
        raw_document={
            "_id": "raw_2",
            "source_id": "source_1",
            "canonical_url": "https://example.com/fire",
            "title_raw": "Izmit'te yangin cikti",
            "content_raw": "Izmit merkezde yangin cikti.",
            "text_raw": "Izmit merkezde yangin cikti.",
            "published_at_raw": "2026-03-23T10:30:00+03:00",
            "scraped_at": "2026-03-23T10:45:00+03:00",
            "language": "tr",
            "domain": "ozgurkocaeli.com.tr",
            "resolved_url": "https://example.com/fire",
        },
        source_document={
            "_id": "source_1",
            "display_name": "Ozgur Kocaeli",
            "base_url": "https://www.ozgurkocaeli.com.tr",
        },
    )

    assert record["category_predicted"] == "yangin"
    assert record["district_predicted"] == "izmit"
    assert record["district_confidence"] == 0.91
    assert record["geocode_status"] == "resolved"
    assert record["geocode_provider"] == "mock"
    assert record["geocode_point"] == {
        "type": "Point",
        "coordinates": [29.9408, 40.7654],
    }
    assert record["pipeline_status"] == "geocoded"


def test_materializer_falls_back_to_district_center_when_geocoding_fails():
    materializer = SourceRecordMaterializer(
        classifier_service=FixedClassifier(),
        ner_service=FixedNER(),
        geocoding_service=FailingGeocoder(),
    )

    record = materializer.materialize(
        raw_document={
            "_id": "raw_3",
            "source_id": "source_1",
            "canonical_url": "https://example.com/fire-fallback",
            "title_raw": "Izmit'te yangin cikti",
            "content_raw": "Izmit merkezde yangin cikti.",
            "text_raw": "Izmit merkezde yangin cikti.",
            "published_at_raw": "2026-03-23T10:30:00+03:00",
            "scraped_at": "2026-03-23T10:45:00+03:00",
            "language": "tr",
            "domain": "ozgurkocaeli.com.tr",
            "resolved_url": "https://example.com/fire-fallback",
        },
        source_document={
            "_id": "source_1",
            "display_name": "Ozgur Kocaeli",
            "base_url": "https://www.ozgurkocaeli.com.tr",
        },
    )

    assert record["district_predicted"] == "izmit"
    assert record["geocode_status"] == "approximate"
    assert record["geocode_provider"] == "district_fallback"
    assert record["geocode_point"] == {
        "type": "Point",
        "coordinates": [29.9408, 40.7654],
    }
    assert record["pipeline_status"] == "geocoded"
