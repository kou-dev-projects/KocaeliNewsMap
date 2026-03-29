from app.pipelines.source_record_materializer import SourceRecordMaterializer


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
    assert record["pipeline_status"] == "classified"
