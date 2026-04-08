import pytest

from app.services.geocoding.cache import RedisGeoCache
from app.services.geocoding.config import GeocodingConfig
from app.services.geocoding.exceptions import ProviderRateLimitError
from app.services.geocoding.factory import build_geocoding_service
from app.services.geocoding.metrics import GeocodingMetrics
from app.services.geocoding.providers.mock import MockGeocodingProvider
from app.services.geocoding.queue import GeocodingQueue
from app.services.geocoding.schemas import GeocodingFailure, GeocodingInput, GeocodingResult
from app.services.geocoding.service import (
    GeocodingService,
    build_geocoding_input_from_ner,
    build_geocoding_inputs_from_ner,
)
from app.services.ner.schemas import LocationCandidate, NERResult


@pytest.fixture
def cfg():
    return GeocodingConfig(
        provider="mock",
        nominatim_url="",
        user_agent="test",
        timeout=5,
        cache_ttl_seconds=3600,
        redis_url="redis://localhost:6379/0",
        max_retries=1,
        min_confidence=0.3,
        opencage_api_key=None,
    )


@pytest.fixture
def svc(cfg):
    return GeocodingService(
        provider=MockGeocodingProvider(),
        cache=RedisGeoCache(cfg.redis_url, cfg.cache_ttl_seconds),
        queue=GeocodingQueue(),
        metrics=GeocodingMetrics(),
        config=cfg,
    )


class RateLimitedProvider:
    name = "dummy"

    def geocode(self, input_data):
        raise ProviderRateLimitError(self.name, retry_after=1.0)


def test_factory_builds_mock_service(cfg):
    service = build_geocoding_service(cfg)
    summary = service.metrics_summary()
    assert isinstance(service, GeocodingService)
    assert summary["provider"] == "mock"


def test_normalized_turkish_i_is_stable():
    assert GeocodingInput(address="Izmit").normalized() == GeocodingInput(
        address="izmit"
    ).normalized()


def test_known_district_returns_result(svc):
    result = svc.geocode(GeocodingInput(address="Izmit"))
    assert isinstance(result, GeocodingResult)
    assert result.lat == pytest.approx(40.7654, abs=0.001)


def test_all_13_districts(svc):
    for district in [
        "Izmit",
        "Gebze",
        "Darica",
        "Golcuk",
        "Hereke",
        "Korfez",
        "Kartepe",
        "Basiskele",
        "Cayirova",
        "Dilovasi",
        "Kandira",
        "Karamursel",
        "Derince",
    ]:
        result = svc.geocode(GeocodingInput(address=district))
        assert isinstance(result, GeocodingResult), f"{district} basarisiz"


def test_unknown_returns_failure(svc):
    result = svc.geocode(GeocodingInput(address="Bilinmeyen XYZ 999"))
    assert isinstance(result, GeocodingFailure)
    assert result.failure_type == "not_found"


def test_failure_has_failure_type(svc):
    result = svc.geocode(GeocodingInput(address="Bilinmeyen yer"))
    assert isinstance(result, GeocodingFailure)
    assert result.failure_type in (
        "not_found",
        "low_confidence",
        "out_of_bounds",
        "provider_error",
    )


def test_district_hint_resolves(svc):
    result = svc.geocode(
        GeocodingInput(address="Yahya Kaptan Mah.", district_hint="Izmit")
    )
    assert isinstance(result, GeocodingResult)


def test_result_in_kocaeli_bounds(svc):
    result = svc.geocode(GeocodingInput(address="Gebze"))
    assert isinstance(result, GeocodingResult)
    assert 40.35 <= result.lat <= 41.15
    assert 29.10 <= result.lng <= 30.90


def test_metrics_incremented_on_success(svc):
    svc.geocode(GeocodingInput(address="Izmit"))
    summary = svc.metrics_summary()
    assert isinstance(summary["cache_available"], bool)
    assert summary["queue_size"] == 0


def test_result_has_provider_version(svc):
    result = svc.geocode(GeocodingInput(address="Golcuk"))
    assert isinstance(result, GeocodingResult)
    assert result.provider_version


def test_news_id_propagated_to_failure(svc):
    result = svc.geocode(GeocodingInput(address="Bilinmeyen", news_id="haber_123"))
    assert isinstance(result, GeocodingFailure)
    assert result.news_id == "haber_123"


def test_metrics_summary_has_required_keys(svc):
    summary = svc.metrics_summary()
    assert "cache_available" in summary
    assert "queue_size" in summary
    assert "provider" in summary


def test_rate_limit_queue_full_returns_queue_full_failure(cfg):
    queue = GeocodingQueue()
    queue._MAX_SIZE = 0
    service = GeocodingService(
        provider=RateLimitedProvider(),
        cache=RedisGeoCache(cfg.redis_url, cfg.cache_ttl_seconds),
        queue=queue,
        metrics=GeocodingMetrics(),
        config=cfg,
    )

    result = service.geocode(GeocodingInput(address="Bu Adres Kesinlikle Yok 12345"))
    assert isinstance(result, GeocodingFailure)
    assert result.failure_type == "queue_full"


def test_build_geocoding_input_prefers_neighborhood_and_district():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[
            LocationCandidate(
                original_text="Cumhuriyet Mahallesi",
                normalized_text="Cumhuriyet Mahallesi",
                score=0.9,
                is_kocaeli_district=False,
                district="Izmit",
                neighborhood="Cumhuriyet Mahallesi",
            )
        ],
        validated_districts=["Izmit"],
        provider="stub",
    )

    result = build_geocoding_input_from_ner(ner_result, news_id="n1")

    assert result is not None
    assert result.address == "Cumhuriyet Mahallesi, Izmit"
    assert result.district_hint == "Izmit"
    assert result.neighborhood == "Cumhuriyet Mahallesi"
    assert result.news_id == "n1"
    assert result.query_string() == "Cumhuriyet Mahallesi, Izmit, Kocaeli"


def test_build_geocoding_input_uses_original_text_when_only_candidate_exists():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[
            LocationCandidate(
                original_text="Yuvacik Baraji",
                normalized_text="Yuvacik Baraji",
                score=0.9,
                is_kocaeli_district=False,
                district=None,
                neighborhood=None,
            )
        ],
        validated_districts=[],
        provider="stub",
    )

    result = build_geocoding_input_from_ner(ner_result)

    assert result is not None
    assert result.address == "Yuvacik Baraji"
    assert result.district_hint is None


def test_build_geocoding_inputs_prioritize_precise_candidate_before_district():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[
            LocationCandidate(
                original_text="Yuvacik Baraji",
                normalized_text="Yuvacik Baraji",
                score=0.95,
                is_kocaeli_district=False,
                district="Basiskele",
            ),
            LocationCandidate(
                original_text="Basiskele",
                normalized_text="Basiskele",
                score=0.8,
                is_kocaeli_district=True,
                district="Basiskele",
            ),
        ],
        validated_districts=["Basiskele"],
        provider="stub",
    )

    results = build_geocoding_inputs_from_ner(ner_result, news_id="n2")

    assert [item.address for item in results[:3]] == [
        "Yuvacik Baraji",
        "Yuvacik Baraji, Basiskele",
        "Basiskele",
    ]
    assert results[0].news_id == "n2"


def test_build_geocoding_inputs_skip_org_like_candidate_when_safe_fallback_is_none():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[
            LocationCandidate(
                original_text="Turkiye Halk Bankasi",
                normalized_text="turkiye halk bankasi",
                score=0.91,
                is_kocaeli_district=False,
                district=None,
            )
        ],
        validated_districts=["Korfez"],
        provider="stub",
    )

    results = build_geocoding_inputs_from_ner(
        ner_result,
        news_id="n3",
        fallback_district=None,
    )

    assert results == []


def test_build_geocoding_inputs_treats_municipality_name_as_generic_even_with_district():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[
            LocationCandidate(
                original_text="Izmit Belediyesi",
                normalized_text="izmit belediyesi",
                score=0.9,
                is_kocaeli_district=False,
                district="Izmit",
            )
        ],
        validated_districts=["Izmit"],
        provider="stub",
    )

    results = build_geocoding_inputs_from_ner(
        ner_result,
        news_id="n4",
        fallback_district="Izmit",
    )

    assert [item.address for item in results] == ["Izmit"]


def test_build_geocoding_inputs_prioritizes_street_level_candidate():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[
            LocationCandidate(
                original_text="Bestekar Amir Ates Caddesi'nde",
                normalized_text="bestekar amir ates caddesi",
                score=0.86,
                is_kocaeli_district=False,
                district=None,
            ),
            LocationCandidate(
                original_text="Yahya Kaptan Mahallesi",
                normalized_text="yahya kaptan mahallesi",
                score=1.0,
                is_kocaeli_district=False,
                district="Izmit",
                neighborhood="Yahya Kaptan Mahallesi",
            ),
        ],
        validated_districts=["Izmit"],
        provider="stub",
    )

    results = build_geocoding_inputs_from_ner(
        ner_result,
        news_id="n5",
        fallback_district="izmit",
    )

    assert results[0].address == "Bestekar Amir Ates Caddesi"
    assert results[0].district_hint == "izmit"


def test_build_geocoding_inputs_put_district_fallback_after_neighborhood_candidates():
    ner_result = NERResult(
        raw_entities=[],
        location_candidates=[
            LocationCandidate(
                original_text="Yenisehir Mahallesi'nde",
                normalized_text="Yenisehir Mahallesi",
                score=0.91,
                is_kocaeli_district=False,
                district="Izmit",
                neighborhood="Yenisehir Mahallesi",
            )
        ],
        validated_districts=["Izmit"],
        provider="stub",
    )

    results = build_geocoding_inputs_from_ner(
        ner_result,
        news_id="n6",
        fallback_district="Izmit",
    )

    assert [item.address for item in results] == [
        "Yenisehir Mahallesi, Izmit",
        "Yenisehir Mahallesi",
        "Izmit",
    ]
