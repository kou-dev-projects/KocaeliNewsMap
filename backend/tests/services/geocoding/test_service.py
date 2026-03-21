import pytest
from app.services.geocoding.factory import build_geocoding_service
from app.services.geocoding.config import GeocodingConfig
from app.services.geocoding.exceptions import ProviderRateLimitError
from app.services.geocoding.schemas import GeocodingInput, GeocodingResult, GeocodingFailure
from app.services.geocoding.metrics import GeocodingMetrics
from app.services.geocoding.cache import RedisGeoCache
from app.services.geocoding.queue import GeocodingQueue
from app.services.geocoding.providers.mock import MockGeocodingProvider
from app.services.geocoding.service import GeocodingService


@pytest.fixture
def cfg():
    return GeocodingConfig(
        provider="mock", nominatim_url="", user_agent="test",
        timeout=5, cache_ttl_seconds=3600,
        redis_url="redis://localhost:6379/0",
        max_retries=1, min_confidence=0.3, opencage_api_key=None,
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
    assert GeocodingInput(address="İzmit").normalized() == GeocodingInput(
        address="izmit"
    ).normalized()


def test_known_district_returns_result(svc):
    r = svc.geocode(GeocodingInput(address="İzmit"))
    assert isinstance(r, GeocodingResult)
    assert r.lat == pytest.approx(40.7654, abs=0.001)

def test_all_12_districts(svc):
    for d in ["İzmit","Gebze","Darıca","Gölcük","Körfez",
              "Kartepe","Başiskele","Çayırova","Dilovası",
              "Kandıra","Karamürsel","Derince"]:
        r = svc.geocode(GeocodingInput(address=d))
        assert isinstance(r, GeocodingResult), f"{d} başarısız"

def test_unknown_returns_failure(svc):
    r = svc.geocode(GeocodingInput(address="Bilinmeyen XYZ 999"))
    assert isinstance(r, GeocodingFailure)
    assert r.failure_type == "not_found"

def test_failure_has_failure_type(svc):
    r = svc.geocode(GeocodingInput(address="Bilinmeyen yer"))
    assert isinstance(r, GeocodingFailure)
    assert r.failure_type in ("not_found", "low_confidence", "out_of_bounds", "provider_error")

def test_district_hint_resolves(svc):
    r = svc.geocode(GeocodingInput(address="Yahya Kaptan Mah.", district_hint="İzmit"))
    assert isinstance(r, GeocodingResult)

def test_result_in_kocaeli_bounds(svc):
    r = svc.geocode(GeocodingInput(address="Gebze"))
    assert isinstance(r, GeocodingResult)
    assert 40.35 <= r.lat <= 41.15
    assert 29.10 <= r.lng <= 30.90

def test_metrics_incremented_on_success(svc):
    svc.geocode(GeocodingInput(address="İzmit"))
    summary = svc.metrics_summary()
    assert summary["cache_available"] is False  # Redis yok, normal
    assert summary["queue_size"] == 0

def test_result_has_provider_version(svc):
    r = svc.geocode(GeocodingInput(address="Gölcük"))
    assert isinstance(r, GeocodingResult)
    assert "mock" in r.provider_version

def test_news_id_propagated_to_failure(svc):
    r = svc.geocode(GeocodingInput(address="Bilinmeyen", news_id="haber_123"))
    assert isinstance(r, GeocodingFailure)
    assert r.news_id == "haber_123"

def test_metrics_summary_has_required_keys(svc):
    summary = svc.metrics_summary()
    assert "cache_available" in summary
    assert "queue_size" in summary
    assert "provider" in summary


def test_rate_limit_queue_full_returns_queue_full_failure(cfg):
    queue = GeocodingQueue()
    queue._MAX_SIZE = 0
    svc = GeocodingService(
        provider=RateLimitedProvider(),
        cache=RedisGeoCache(cfg.redis_url, cfg.cache_ttl_seconds),
        queue=queue,
        metrics=GeocodingMetrics(),
        config=cfg,
    )

    result = svc.geocode(GeocodingInput(address="İzmit"))
    assert isinstance(result, GeocodingFailure)
    assert result.failure_type == "queue_full"
