from unittest.mock import MagicMock, patch

import pytest

from app.services.geocoding.config import GeocodingConfig
from app.services.geocoding.exceptions import ProviderRateLimitError
from app.services.geocoding.providers.mock import MockGeocodingProvider
from app.services.geocoding.providers.nominatim import NominatimProvider
from app.services.geocoding.schemas import GeocodingInput


@pytest.fixture
def cfg():
    return GeocodingConfig(
        provider="nominatim",
        nominatim_url="https://nominatim.openstreetmap.org",
        user_agent="PULSE-test/1.0",
        timeout=5,
        cache_ttl_seconds=3600,
        redis_url="redis://localhost:6379/0",
        max_retries=1,
        min_confidence=0.3,
        opencage_api_key=None,
    )


@pytest.fixture
def provider(cfg):
    return NominatimProvider(cfg)


def _hit(
    *,
    lat="40.7654",
    lon="29.9408",
    display="Izmit, Kocaeli, Turkiye",
    importance=0.75,
    district="Izmit",
    result_type="city",
    addresstype="city",
):
    return {
        "lat": lat,
        "lon": lon,
        "display_name": display,
        "importance": importance,
        "type": result_type,
        "addresstype": addresstype,
        "address": {"city": district, "county": "Kocaeli"},
        "namedetails": {"name": display.split(",")[0]},
    }


def _mock_resp(*results, status=200):
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = list(results) if status == 200 else []
    mock.raise_for_status = MagicMock()
    mock.headers = {}
    return mock


def test_nominatim_returns_result(provider):
    with patch("requests.get", return_value=_mock_resp(_hit())):
        result = provider.geocode(GeocodingInput(address="Izmit, Kocaeli"))
    assert result is not None
    assert abs(result.lat - 40.7654) < 0.001
    assert result.source == "nominatim"
    assert result.provider_version == "nominatim@1.1"


def test_nominatim_empty_response_returns_none(provider):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = []
    mock.raise_for_status = MagicMock()
    mock.headers = {}
    with patch("requests.get", return_value=mock):
        result = provider.geocode(GeocodingInput(address="Bilinmeyen"))
    assert result is None


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
    with patch(
        "requests.get",
        return_value=_mock_resp(_hit(display="Izmir, Turkiye", district="Izmir")),
    ):
        result = provider.geocode(GeocodingInput(address="Test"))
    assert result is not None
    assert result.confidence < 0.5


def test_nominatim_query_includes_kocaeli_and_uses_multi_result_limit(provider):
    with patch("requests.get", return_value=_mock_resp(_hit())) as mock_get:
        provider.geocode(GeocodingInput(address="Yahya Kaptan Mah."))
    params = mock_get.call_args[1]["params"]
    assert "Kocaeli" in params["q"]
    assert params["limit"] == 5
    assert params["format"] == "jsonv2"


def test_nominatim_prefers_precise_hit_over_administrative_hit(provider):
    district_hit = _hit(
        display="Karamursel, Kocaeli, Turkiye",
        district="Karamursel",
        result_type="city",
        addresstype="city",
    )
    precise_hit = _hit(
        lat="40.6290",
        lon="29.5916",
        display="Ihsaniye Baraji, Karamursel, Kocaeli, Turkiye",
        district="Karamursel",
        result_type="reservoir",
        addresstype="reservoir",
    )
    with patch("requests.get", return_value=_mock_resp(district_hit, precise_hit)):
        result = provider.geocode(
            GeocodingInput(address="Ihsaniye Baraji", district_hint="Karamursel")
        )

    assert result is not None
    assert result.display_name.startswith("Ihsaniye Baraji")
    assert result.lng == pytest.approx(29.5916, abs=0.001)
    assert result.confidence >= 0.3


def test_mock_returns_all_13_districts():
    provider = MockGeocodingProvider()
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
        result = provider.geocode(GeocodingInput(address=district))
        assert result is not None, f"{district} mock'ta bulunamadi"


def test_mock_unknown_returns_none():
    provider = MockGeocodingProvider()
    result = provider.geocode(GeocodingInput(address="Bilinmeyen XYZ"))
    assert result is None


def test_mock_district_hint_fallback():
    provider = MockGeocodingProvider()
    result = provider.geocode(
        GeocodingInput(address="Yahya Kaptan Mah.", district_hint="Izmit")
    )
    assert result is not None
    assert result.district == "izmit"
