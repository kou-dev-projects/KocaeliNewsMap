import pytest
from fastapi import HTTPException, Response

from app.api.system import diagnostics, livez, readyz


def test_livez_returns_ok():
    assert livez() == {"status": "ok"}


def test_readyz_returns_ready_when_dependencies_are_up(monkeypatch):
    monkeypatch.setattr("app.api.system._check_mongo", lambda: True)
    monkeypatch.setattr("app.api.system._check_redis", lambda: True)

    response = Response()
    payload = readyz(response)

    assert response.status_code == 200
    assert payload == {
        "status": "ready",
        "checks": {
            "mongo": "ok",
            "redis": "ok",
        },
    }


def test_readyz_returns_503_when_dependency_is_down(monkeypatch):
    monkeypatch.setattr("app.api.system._check_mongo", lambda: False)
    monkeypatch.setattr("app.api.system._check_redis", lambda: True)

    response = Response()
    payload = readyz(response)

    assert response.status_code == 503
    assert payload == {
        "status": "not_ready",
        "checks": {
            "mongo": "unavailable",
            "redis": "ok",
        },
    }


def test_diagnostics_returns_detail_when_allowed(monkeypatch):
    monkeypatch.setattr("app.api.system.settings.app_env", "dev")
    monkeypatch.setattr(
        "app.api.system._check_mongo_detailed",
        lambda: (False, "ServerSelectionTimeoutError: mongo unavailable"),
    )
    monkeypatch.setattr("app.api.system._check_redis_detailed", lambda: (True, None))

    response = Response()
    payload = diagnostics(response)

    assert response.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["checks"]["mongo"]["status"] == "error"
    assert payload["checks"]["mongo"]["error"] == "ServerSelectionTimeoutError: mongo unavailable"
    assert payload["checks"]["redis"]["status"] == "ok"


def test_diagnostics_requires_key_in_production(monkeypatch):
    monkeypatch.setattr("app.api.system.settings.app_env", "production")
    monkeypatch.setattr("app.api.system.settings.scrape_trigger_api_key", "secret-token")

    with pytest.raises(HTTPException) as exc_info:
        diagnostics(Response(), x_api_key=None)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "diagnostics_access_denied"


def test_diagnostics_accepts_valid_key_in_production(monkeypatch):
    monkeypatch.setattr("app.api.system.settings.app_env", "production")
    monkeypatch.setattr("app.api.system.settings.scrape_trigger_api_key", "secret-token")
    monkeypatch.setattr("app.api.system._check_mongo_detailed", lambda: (True, None))
    monkeypatch.setattr("app.api.system._check_redis_detailed", lambda: (True, None))

    response = Response()
    payload = diagnostics(response, x_api_key="secret-token")

    assert response.status_code == 200
    assert payload["status"] == "ok"
