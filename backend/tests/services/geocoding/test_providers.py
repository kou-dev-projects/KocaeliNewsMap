import pytest
from unittest.mock import patch, MagicMock
from app.services.geocoding.config import GeocodingConfig
from app.services.geocoding.providers.nominatim import NominatimProvider
from app.services.geocoding.providers.mock import MockGeocodingProvider
from app.services.geocoding.schemas import GeocodingInput
from app.services.geocoding.exceptions import ProviderRateLimitError


@pytest.fixture
def cfg():
    return GeocodingConfig(
        provider="nominatim", nominatim_url="https://nominatim.openstreetmap.org",
        user_agent="PULSE-test/1.0", timeout=5, cache_ttl_seconds=3600,
        redis_url="redis://localhost:6379/0", max_retries=1,
        min_confidence=0.3, opencage_api_key=None,
    )


@pytest.fixture
def provider(cfg):
    return NominatimProvider(cfg)


def _mock_resp(lat="40.7654", lon="29.9408", display="İzmit, Kocaeli, Türkiye", status=200):
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = [{
        "lat": lat, "lon": lon,
        "display_name": display,
        "importance": 0.75,
        "address": {"city": "İzmit", "county": "Kocaeli"},
    }] if status == 200 else []
    mock.raise_for_status = MagicMock()
    mock.headers = {}
    return mock


# --- Nominatim ---

def test_nominatim_returns_result(provider):
    with patch("requests.get", return_value=_mock_resp()):
        r = provider.geocode(GeocodingInput(address="İzmit, Kocaeli"))
    assert r is not None
    assert abs(r.lat - 40.7654) < 0.001
    assert r.source == "nominatim"
    assert r.provider_version == "nominatim@1.0"


def test_nominatim_empty_response_returns_none(provider):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = []
    mock.raise_for_status = MagicMock()
    mock.headers = {}
    with patch("requests.get", return_value=mock):
        r = provider.geocode(GeocodingInput(address="Bilinmeyen"))
    assert r is None


def test_nominatim_429_raises_rate_limit(provider):
    mock = MagicMock()
    mock.status_code = 429
    mock.headers = {"Retry-After": "2.0"}
    mock.raise_for_status = MagicMock()
    with patch("requests.get", return_value=mock):
        with pytest.raises(ProviderRateLimitError) as exc_info:
            provider.geocode(GeocodingInput(address="Test"))
    assert exc_info.value.retry_after == 2.0


def test_nominatim_non_kocaeli_low_confidence(provider):
    with patch("requests.get", return_value=_mock_resp(display="İzmir, Türkiye")):
        r = provider.geocode(GeocodingInput(address="Test"))
    assert r is not None
    assert r.confidence < 0.5


def test_nominatim_query_includes_kocaeli(provider):
    with patch("requests.get", return_value=_mock_resp()) as mock_get:
        provider.geocode(GeocodingInput(address="Yahya Kaptan Mah."))
    params = mock_get.call_args[1]["params"]
    assert "Kocaeli" in params["q"]


# --- Mock ---

def test_mock_returns_all_12_districts():
    p = MockGeocodingProvider()
    for d in ["İzmit","Gebze","Darıca","Gölcük","Körfez",
              "Kartepe","Başiskele","Çayırova","Dilovası",
              "Kandıra","Karamürsel","Derince"]:
        r = p.geocode(GeocodingInput(address=d))
        assert r is not None, f"{d} mock'ta bulunamadı"


def test_mock_unknown_returns_none():
    p = MockGeocodingProvider()
    r = p.geocode(GeocodingInput(address="Bilinmeyen XYZ"))
    assert r is None


def test_mock_district_hint_fallback():
    p = MockGeocodingProvider()
    r = p.geocode(GeocodingInput(address="Yahya Kaptan Mah.", district_hint="İzmit"))
    assert r is not None
    assert r.district == "izmit"