from app.services.geocoding.metrics import GeocodingMetrics


def test_success_increments_counter():
    m = GeocodingMetrics()
    m.record_success("nominatim", "izmit", 0.85)
    assert m.total_success == 1
    assert m.total_requests == 1

def test_failure_increments_by_type():
    m = GeocodingMetrics()
    m.record_failure("Test", "not_found", "bulunamadı")
    assert m.failure_by_type["not_found"] == 1

def test_cache_hit_rate():
    m = GeocodingMetrics()
    m.record_success("cache", "izmit", 0.9)
    m.record_success("nominatim", "gebze", 0.8)
    summary = m.summary()
    assert summary["success_rate"] == 1.0

def test_summary_has_all_keys():
    m = GeocodingMetrics()
    s = m.summary()
    assert "total_requests" in s
    assert "success_rate" in s
    assert "cache_hit_rate" in s
    assert "failure_by_type" in s
    assert "top_failure_types" in s


def test_rate_limit_counts_as_failure():
    m = GeocodingMetrics()
    m.record_rate_limit("nominatim", 1.0, address="İzmit")
    assert m.total_requests == 1
    assert m.total_failure == 1
    assert m.failure_by_type["rate_limit"] == 1
    assert m.failed_addresses == ["İzmit"]
