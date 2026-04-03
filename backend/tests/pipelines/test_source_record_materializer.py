from app.domain.enums import NewsCategory
from app.pipelines.location_versions import (
    GAZETTEER_VERSION,
    LIVE_LOCATION_BENCHMARK_VERSION,
    LOCATION_PIPELINE_VERSION,
    LOGICAL_LOCATION_CATALOG_VERSION,
    SOURCE_RECORD_SCHEMA_VERSION,
)
from app.pipelines.source_record_materializer import SourceRecordMaterializer
from app.services.classifier.schemas import ClassificationResult
from app.services.geocoding.schemas import GeocodingFailure, GeocodingResult
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
    assert record["location_pipeline_version"] == LOCATION_PIPELINE_VERSION
    assert record["gazetteer_version"] == GAZETTEER_VERSION
    assert record["logical_catalog_version"] == LOGICAL_LOCATION_CATALOG_VERSION
    assert record["location_benchmark_version"] == LIVE_LOCATION_BENCHMARK_VERSION
    assert record["schema_version"] == SOURCE_RECORD_SCHEMA_VERSION


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


class PreciseLocationNER:
    def extract_locations(self, input_data):
        return NERResult(
            raw_entities=[],
            location_candidates=[
                LocationCandidate(
                    original_text="Yuvacik Baraji",
                    normalized_text="yuvacik baraji",
                    score=0.95,
                    is_kocaeli_district=False,
                    district="Basiskele",
                ),
                LocationCandidate(
                    original_text="Basiskele",
                    normalized_text="basiskele",
                    score=0.8,
                    is_kocaeli_district=True,
                    district="Basiskele",
                ),
            ],
            validated_districts=["Basiskele"],
            provider="fixed_ner",
        )


class MultiAttemptGeocoder:
    def __init__(self):
        self.queries = []

    def geocode(self, input_data):
        self.queries.append(input_data.address)
        if "Yuvacik Baraji" in input_data.address:
            return GeocodingResult(
                address=input_data.address,
                lat=40.6781,
                lng=29.9325,
                display_name="Yuvacik Baraji, Basiskele, Kocaeli, Turkiye",
                confidence=0.93,
                source="mock",
                provider_version="test",
                district="Basiskele",
            )
        return GeocodingFailure(
            address=input_data.address,
            reason="Not found",
            failure_type="not_found",
            news_id=input_data.news_id,
        )


class CinemaGeocoder:
    def __init__(self):
        self.queries = []

    def geocode(self, input_data):
        self.queries.append(input_data.address)
        if input_data.address == "Paribu Cineverse 41 Burda AVM":
            return GeocodingResult(
                address=input_data.address,
                lat=40.7751,
                lng=29.9462,
                display_name="Paribu Cineverse 41 Burda AVM, Izmit, Kocaeli, Turkiye",
                confidence=0.96,
                source="mock",
                provider_version="test",
                district="Izmit",
            )
        return GeocodingFailure(
            address=input_data.address,
            reason="Not found",
            failure_type="not_found",
            news_id=input_data.news_id,
        )


class MovieRoundupClassifier:
    def classify(self, input_data):
        return ClassificationResult(
            category=NewsCategory.KULTUREL_ETKINLIK,
            confidence=0.92,
            method="movie_classifier",
        )


class NoLocationNER:
    def extract_locations(self, input_data):
        return NERResult(
            raw_entities=[],
            location_candidates=[],
            validated_districts=[],
            provider="fixed_ner",
        )


def test_materializer_marks_district_level_geocodes_as_approximate():
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
    assert record["geocode_status"] == "approximate"
    assert record["geocode_provider"] == "mock"
    assert record["geocode_provider_version"] == "test"
    assert record["location_pipeline_version"] == LOCATION_PIPELINE_VERSION
    assert record["geocode_point"] == {
        "type": "Point",
        "coordinates": [29.9408, 40.7654],
    }
    assert record["pipeline_status"] == "geocoded"


def test_materializer_keeps_approximate_status_without_fake_coordinates():
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
    assert "geocode_provider_version" not in record
    assert record["logical_catalog_version"] == LOGICAL_LOCATION_CATALOG_VERSION
    assert "geocode_point" not in record
    assert record["pipeline_status"] == "geocoded"


def test_materializer_tries_precise_queries_before_district_only_fallback():
    geocoder = MultiAttemptGeocoder()
    materializer = SourceRecordMaterializer(
        classifier_service=FixedClassifier(),
        ner_service=PreciseLocationNER(),
        geocoding_service=geocoder,
    )

    record = materializer.materialize(
        raw_document={
            "_id": "raw_4",
            "source_id": "source_1",
            "canonical_url": "https://example.com/baraj",
            "title_raw": "Yuvacik Baraji'nda calisma yapildi",
            "content_raw": "Basiskele Yuvacik Baraji cevresinde bakim yapildi.",
            "text_raw": "Basiskele Yuvacik Baraji cevresinde bakim yapildi.",
            "published_at_raw": "2026-03-23T10:30:00+03:00",
            "scraped_at": "2026-03-23T10:45:00+03:00",
            "language": "tr",
            "domain": "ozgurkocaeli.com.tr",
            "resolved_url": "https://example.com/baraj",
        },
        source_document={
            "_id": "source_1",
            "display_name": "Ozgur Kocaeli",
            "base_url": "https://www.ozgurkocaeli.com.tr",
        },
    )

    assert geocoder.queries[0] == "Yuvacik Baraji"
    assert record["district_predicted"] == "basiskele"
    assert record["geocode_status"] == "resolved"
    assert record["geocode_provider_version"] == "test"
    assert record["geocode_point"] == {
        "type": "Point",
        "coordinates": [29.9325, 40.6781],
    }


def test_materializer_uses_logical_cinema_marker_when_story_has_no_precise_place():
    geocoder = CinemaGeocoder()
    materializer = SourceRecordMaterializer(
        classifier_service=MovieRoundupClassifier(),
        ner_service=NoLocationNER(),
        geocoding_service=geocoder,
    )

    record = materializer.materialize(
        raw_document={
            "_id": "raw_5",
            "source_id": "source_1",
            "canonical_url": "https://example.com/cinema",
            "title_raw": "Sinema salonlarinda 6 yeni film",
            "content_raw": "Bu hafta sinema salonlarinda yeni filmler vizyona giriyor.",
            "text_raw": "Bu hafta sinema salonlarinda yeni filmler vizyona giriyor.",
            "published_at_raw": "2026-03-23T10:30:00+03:00",
            "scraped_at": "2026-03-23T10:45:00+03:00",
            "language": "tr",
            "domain": "bizimyaka.com.tr",
            "resolved_url": "https://example.com/cinema",
        },
        source_document={
            "_id": "source_1",
            "display_name": "Bizim Yaka",
            "base_url": "https://bizimyaka.com.tr",
        },
    )

    assert geocoder.queries[0] == "Paribu Cineverse 41 Burda AVM"
    assert record["district_predicted"] == "izmit"
    assert record["geocode_status"] == "approximate"
    assert record["location_text_extracted"] == "Paribu Cineverse 41 Burda AVM"
    assert record["location_resolution_method"] == "logic_cinema_release"
    assert record["location_benchmark_version"] == LIVE_LOCATION_BENCHMARK_VERSION
    assert record["geocode_provider_version"] == "test"
    assert record["geocode_point"] == {
        "type": "Point",
        "coordinates": [29.9462, 40.7751],
    }


class GenericOfficeNER:
    def extract_locations(self, input_data):
        return NERResult(
            raw_entities=[],
            location_candidates=[
                LocationCandidate(
                    original_text="Belediyesi",
                    normalized_text="belediyesi",
                    score=0.83,
                    is_kocaeli_district=False,
                    district="Kartepe",
                )
            ],
            validated_districts=["Kartepe"],
            provider="fixed_ner",
        )


def test_materializer_skips_generic_location_tokens_and_falls_back_to_district():
    materializer = SourceRecordMaterializer(
        classifier_service=MovieRoundupClassifier(),
        ner_service=GenericOfficeNER(),
        geocoding_service=FixedGeocoder(),
    )

    record = materializer.materialize(
        raw_document={
            "_id": "raw_6",
            "source_id": "source_1",
            "canonical_url": "https://example.com/office",
            "title_raw": "Kartepe Belediyesi farkindalik egitimi duzenledi",
            "content_raw": "Kartepe Belediyesi tarafindan duzenlenen egitim vatandaslarla bulustu.",
            "text_raw": "Kartepe Belediyesi tarafindan duzenlenen egitim vatandaslarla bulustu.",
            "published_at_raw": "2026-03-23T10:30:00+03:00",
            "scraped_at": "2026-03-23T10:45:00+03:00",
            "language": "tr",
            "domain": "yenikocaeli.com",
            "resolved_url": "https://example.com/office",
        },
        source_document={
            "_id": "source_1",
            "display_name": "Yeni Kocaeli",
            "base_url": "https://www.yenikocaeli.com",
        },
    )

    assert record["district_predicted"] == "kartepe"
    assert record["location_text_extracted"] == "Kartepe"
    assert record["geocode_status"] == "approximate"
