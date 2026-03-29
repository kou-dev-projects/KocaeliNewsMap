from fastapi import Response

from app.api.system import health


def test_health_returns_ok_when_dependencies_are_ready(monkeypatch):
    monkeypatch.setattr("app.api.system._check_mongo", lambda: (True, None))
    monkeypatch.setattr("app.api.system._check_redis", lambda: (True, None))

    response = Response()
    payload = health(response)

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["checks"]["mongo"]["status"] == "ok"
    assert payload["checks"]["redis"]["status"] == "ok"


def test_health_returns_503_when_redis_is_down(monkeypatch):
    monkeypatch.setattr("app.api.system._check_mongo", lambda: (True, None))
    monkeypatch.setattr(
        "app.api.system._check_redis",
        lambda: (False, "ConnectionError: redis unavailable"),
    )

    response = Response()
    payload = health(response)

    assert response.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["checks"]["mongo"]["status"] == "ok"
    assert payload["checks"]["redis"]["status"] == "error"
    assert payload["checks"]["redis"]["error"] == "ConnectionError: redis unavailable"


def test_health_returns_503_when_mongo_is_down(monkeypatch):
    monkeypatch.setattr(
        "app.api.system._check_mongo",
        lambda: (False, "ServerSelectionTimeoutError: mongo unavailable"),
    )
    monkeypatch.setattr("app.api.system._check_redis", lambda: (True, None))

    response = Response()
    payload = health(response)

    assert response.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["checks"]["mongo"]["status"] == "error"
    assert payload["checks"]["mongo"]["error"] == "ServerSelectionTimeoutError: mongo unavailable"
    assert payload["checks"]["redis"]["status"] == "ok"
