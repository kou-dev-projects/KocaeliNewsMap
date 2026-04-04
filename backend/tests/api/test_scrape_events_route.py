from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.scrape_events import _HEARTBEAT_SENTINEL

API_KEY = "secret"

_SAMPLE_FIELDS = {
    "event": "job_submitted",
    "message": "Manual scrape job queued",
    "job_id": "abc123",
    "source": "ozgurkocaeli.com.tr",
    "trigger_type": "manual",
    "status": "pending",
    "attempt_count": "2",
    "timestamp": "1711900000.5",
    "details": '{"result_status": "ok"}',
}


class FakeScrapeEventReader:
    """Yields a fixed event sequence, then stops."""

    def __init__(self, events=None, **kwargs):
        self.init_kwargs = kwargs
        self._events = events if events is not None else []
        # Capture what stream() was called with for assertions.
        self.stream_last_id: str | None = None
        self.stream_job_id_filter: str | None = None

    async def stream(self, *, last_id="$", job_id_filter=None):
        self.stream_last_id = last_id
        self.stream_job_id_filter = job_id_filter
        for item in self._events:
            yield item


@pytest.fixture(autouse=True)
def _reset_scrape_auth(monkeypatch):
    monkeypatch.setattr("app.routes.scrape.settings.scrape_trigger_api_key", API_KEY)
    monkeypatch.setattr("app.routes.scrape.settings.scrape_events_heartbeat_seconds", 999)


def _authorized_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"X-API-Key": API_KEY}
    if extra:
        headers.update(extra)
    return headers




def _make_reader_with(events, monkeypatch) -> FakeScrapeEventReader:
    """Patches ScrapeEventReader and returns the fake instance."""
    instance = FakeScrapeEventReader(events=events)

    class _FakeClass:
        def __init__(self, **kwargs):
            instance.init_kwargs = kwargs

        async def stream(self, *, last_id="$", job_id_filter=None):
            instance.stream_last_id = last_id
            instance.stream_job_id_filter = job_id_filter
            for item in events:
                yield item

    monkeypatch.setattr("app.routes.scrape.ScrapeEventReader", _FakeClass)
    return instance


def _collect_sse_frames(raw: bytes) -> list[str]:
    """Split raw SSE bytes into individual frames."""
    return [f for f in raw.decode().split("\n\n") if f.strip()]




class TestScrapeEventsRoute:

    def test_latest_returns_idle_shape_when_no_run_exists(self, monkeypatch):
        monkeypatch.setattr("app.routes.scrape.get_latest_scrape_run", lambda: None)

        with TestClient(app) as client:
            response = client.get("/api/v1/scrape/latest", headers=_authorized_headers())

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "idle"
        assert payload["events"] == []
        assert payload["event_count"] == 0

    def test_latest_returns_persisted_run(self, monkeypatch):
        monkeypatch.setattr(
            "app.routes.scrape.get_latest_scrape_run",
            lambda: {
                "job_id": "abc123",
                "status": "running",
                "source": None,
                "trigger_type": "refresh",
                "started_at": 1.0,
                "updated_at": 2.0,
                "event_count": 1,
                "events": [
                    {
                        "event": "job_started",
                        "message": "Scrape job started",
                        "timestamp": 1.0,
                        "job_id": "abc123",
                        "source": None,
                        "trigger_type": "refresh",
                        "status": "running",
                        "attempt_count": None,
                        "details": {},
                    }
                ],
            },
        )

        with TestClient(app) as client:
            response = client.get("/api/v1/scrape/latest", headers=_authorized_headers())

        assert response.status_code == 200
        payload = response.json()
        assert payload["job_id"] == "abc123"
        assert payload["event_count"] == 1
        assert payload["events"][0]["event"] == "job_started"

    def test_media_type_is_event_stream(self, monkeypatch):
        _make_reader_with([], monkeypatch)

        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get("/api/v1/scrape/events", headers=_authorized_headers())

        assert "text/event-stream" in response.headers["content-type"]

    def test_cache_control_and_nginx_headers(self, monkeypatch):
        _make_reader_with([], monkeypatch)

        with TestClient(app) as client:
            response = client.get("/api/v1/scrape/events", headers=_authorized_headers())

        assert response.headers.get("cache-control") == "no-cache"
        assert response.headers.get("x-accel-buffering") == "no"

    def test_auth_returns_401_when_key_configured_and_missing(self, monkeypatch):
        _make_reader_with([], monkeypatch)

        with TestClient(app) as client:
            response = client.get("/api/v1/scrape/events")

        assert response.status_code == 401

    def test_auth_accepts_valid_api_key(self, monkeypatch):
        _make_reader_with([], monkeypatch)

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/scrape/events",
                headers=_authorized_headers(),
            )

        assert response.status_code == 200

    def test_sse_frame_format_has_id_event_data(self, monkeypatch):
        _make_reader_with([("1680000000-0", _SAMPLE_FIELDS)], monkeypatch)

        with TestClient(app) as client:
            response = client.get("/api/v1/scrape/events", headers=_authorized_headers())

        frames = _collect_sse_frames(response.content)
        assert len(frames) >= 1
        frame = frames[0]
        assert "id: 1680000000-0" in frame
        assert "event: job_submitted" in frame
        assert "data: " in frame

    def test_details_not_double_encoded(self, monkeypatch):
        """details must arrive as a JSON object, not a JSON string."""
        _make_reader_with([("1-0", _SAMPLE_FIELDS)], monkeypatch)

        with TestClient(app) as client:
            response = client.get("/api/v1/scrape/events", headers=_authorized_headers())

        frames = _collect_sse_frames(response.content)
        data_line = next(l for l in frames[0].splitlines() if l.startswith("data: "))
        event_data = json.loads(data_line[len("data: "):])

        # details must already be a dict — not a string requiring a second parse
        assert isinstance(event_data["details"], dict)
        assert event_data["details"] == {"result_status": "ok"}

    def test_attempt_count_and_timestamp_are_native_types(self, monkeypatch):
        _make_reader_with([("2-0", _SAMPLE_FIELDS)], monkeypatch)

        with TestClient(app) as client:
            response = client.get("/api/v1/scrape/events", headers=_authorized_headers())

        frames = _collect_sse_frames(response.content)
        data_line = next(l for l in frames[0].splitlines() if l.startswith("data: "))
        event_data = json.loads(data_line[len("data: "):])

        assert isinstance(event_data["attempt_count"], int)
        assert event_data["attempt_count"] == 2
        assert isinstance(event_data["timestamp"], float)

    def test_heartbeat_frame_is_sse_comment(self, monkeypatch):
        _make_reader_with([(_HEARTBEAT_SENTINEL, {})], monkeypatch)

        with TestClient(app) as client:
            response = client.get("/api/v1/scrape/events", headers=_authorized_headers())

        assert ": ping" in response.text

    def test_last_event_id_passed_to_stream(self, monkeypatch):
        captured = {}

        class _CapturingReader:
            def __init__(self, **kwargs):
                pass

            async def stream(self, *, last_id="$", job_id_filter=None):
                captured["last_id"] = last_id
                if False:
                    yield  # make it an async generator

        monkeypatch.setattr("app.routes.scrape.ScrapeEventReader", _CapturingReader)

        with TestClient(app) as client:
            client.get(
                "/api/v1/scrape/events",
                headers=_authorized_headers({"last-event-id": "1680000000-5"}),
            )

        assert captured.get("last_id") == "1680000000-5"

    def test_default_last_id_is_dollar(self, monkeypatch):
        captured = {}

        class _CapturingReader:
            def __init__(self, **kwargs):
                pass

            async def stream(self, *, last_id="$", job_id_filter=None):
                captured["last_id"] = last_id
                if False:
                    yield

        monkeypatch.setattr("app.routes.scrape.ScrapeEventReader", _CapturingReader)

        with TestClient(app) as client:
            client.get("/api/v1/scrape/events", headers=_authorized_headers())

        assert captured.get("last_id") == "$"

    def test_job_id_filter_passed_to_stream(self, monkeypatch):
        captured = {}

        class _CapturingReader:
            def __init__(self, **kwargs):
                pass

            async def stream(self, *, last_id="$", job_id_filter=None):
                captured["job_id_filter"] = job_id_filter
                if False:
                    yield

        monkeypatch.setattr("app.routes.scrape.ScrapeEventReader", _CapturingReader)

        with TestClient(app) as client:
            client.get("/api/v1/scrape/events?job_id=abc123", headers=_authorized_headers())

        assert captured.get("job_id_filter") == "abc123"

    def test_invalid_last_event_id_falls_back_to_dollar(self, monkeypatch):
        """Malformed Last-Event-ID should not be passed to Redis — falls back to $."""
        captured = {}

        class _CapturingReader:
            def __init__(self, **kwargs):
                pass

            async def stream(self, *, last_id="$", job_id_filter=None):
                captured["last_id"] = last_id
                if False:
                    yield

        monkeypatch.setattr("app.routes.scrape.ScrapeEventReader", _CapturingReader)

        with TestClient(app) as client:
            client.get(
                "/api/v1/scrape/events",
                headers=_authorized_headers({"last-event-id": "DROP TABLE events;"}),
            )

        assert captured.get("last_id") == "$"

    def test_valid_stream_id_passes_through(self, monkeypatch):
        """A well-formed Redis Stream ID like '1680000000000-5' passes validation."""
        captured = {}

        class _CapturingReader:
            def __init__(self, **kwargs):
                pass

            async def stream(self, *, last_id="$", job_id_filter=None):
                captured["last_id"] = last_id
                if False:
                    yield

        monkeypatch.setattr("app.routes.scrape.ScrapeEventReader", _CapturingReader)

        with TestClient(app) as client:
            client.get(
                "/api/v1/scrape/events",
                headers=_authorized_headers({"last-event-id": "1680000000000-5"}),
            )

        assert captured.get("last_id") == "1680000000000-5"
