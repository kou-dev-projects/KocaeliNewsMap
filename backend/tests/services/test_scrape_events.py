from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch


from app.services.scrape_events import (
    ScrapeEvent,
    ScrapeEventPublisher,
    ScrapeEventReader,
    _HEARTBEAT_SENTINEL,
    _MAX_PERSISTED_SCRAPE_EVENTS,
    _SCRAPE_EVENT_STREAM_KEY,
    get_latest_scrape_run,
    get_scrape_event_publisher,
)


#

def _make_publisher(redis_client=None, scrape_run_collection=None) -> ScrapeEventPublisher:
    return ScrapeEventPublisher(
        redis_url="redis://localhost:6379/0",
        stream_maxlen=500,
        redis_client=redis_client,
        scrape_run_collection=scrape_run_collection or MagicMock(),
    )


def _make_event(**kwargs) -> ScrapeEvent:
    defaults = dict(
        event="job_submitted",
        message="test event",
        job_id="abc123",
        source="ozgurkocaeli.com.tr",
        trigger_type="manual",
        status="pending",
    )
    defaults.update(kwargs)
    return ScrapeEvent(**defaults)




class TestScrapeEventPublisher:

    def test_publish_calls_xadd_with_correct_stream_key(self):
        fake_redis = MagicMock()
        pub = _make_publisher(redis_client=fake_redis)

        pub.publish(_make_event())

        fake_redis.xadd.assert_called_once()
        assert fake_redis.xadd.call_args.args[0] == _SCRAPE_EVENT_STREAM_KEY

    def test_publish_includes_all_required_fields(self):
        fake_redis = MagicMock()
        pub = _make_publisher(redis_client=fake_redis)

        pub.publish(_make_event(attempt_count=2, details={"error": "boom"}))

        payload: dict = fake_redis.xadd.call_args.args[1]
        assert payload["event"] == "job_submitted"
        assert payload["job_id"] == "abc123"
        assert payload["source"] == "ozgurkocaeli.com.tr"
        assert payload["attempt_count"] == "2"
        assert json.loads(payload["details"]) == {"error": "boom"}

    def test_publish_uses_approximate_maxlen(self):
        fake_redis = MagicMock()
        pub = _make_publisher(redis_client=fake_redis)

        pub.publish(_make_event())

        call_kwargs = fake_redis.xadd.call_args.kwargs
        assert call_kwargs.get("approximate") is True
        assert call_kwargs.get("maxlen") == 500

    def test_publish_serializes_non_string_details_safely(self):
        """default=str prevents crashes on ObjectId / datetime in details."""
        fake_redis = MagicMock()
        pub = _make_publisher(redis_client=fake_redis)

        class _Unserializable:
            def __repr__(self):
                return "unserializable"

        pub.publish(_make_event(details={"obj": _Unserializable()}))
        payload: dict = fake_redis.xadd.call_args.args[1]
        details = json.loads(payload["details"])
        assert "obj" in details

    def test_publish_resets_client_on_xadd_error(self):
        fake_redis = MagicMock()
        fake_redis.xadd.side_effect = RuntimeError("redis gone")
        pub = _make_publisher(redis_client=fake_redis)

        pub.publish(_make_event())  # must not raise

        assert pub._redis is None  # reset for reconnect

    def test_publish_is_noop_when_redis_unavailable(self):
        pub = _make_publisher(redis_client=None)

        with patch.object(pub, "_connect", return_value=None):
            pub.publish(_make_event())  # must not raise

    def test_none_attempt_count_serialized_as_empty_string(self):
        fake_redis = MagicMock()
        pub = _make_publisher(redis_client=fake_redis)

        pub.publish(_make_event())

        payload: dict = fake_redis.xadd.call_args.args[1]
        assert payload["attempt_count"] == ""

    def test_get_scrape_event_publisher_is_singleton(self, monkeypatch):
        monkeypatch.setattr("app.services.scrape_events._publisher", None)
        a = get_scrape_event_publisher()
        b = get_scrape_event_publisher()
        assert a is b

    def test_injected_client_skips_lazy_connect(self):
        fake_redis = MagicMock()
        pub = _make_publisher(redis_client=fake_redis)

        with patch.object(pub, "_connect") as mock_connect:
            pub.publish(_make_event())

        mock_connect.assert_not_called()

    def test_publish_replaces_latest_run_on_job_submitted(self):
        fake_redis = MagicMock()
        fake_collection = MagicMock()
        pub = _make_publisher(
            redis_client=fake_redis,
            scrape_run_collection=fake_collection,
        )

        pub.publish(_make_event())

        fake_collection.replace_one.assert_called_once()
        persisted = fake_collection.replace_one.call_args.args[1]
        assert persisted["job_id"] == "abc123"
        assert persisted["event_count"] == 1
        assert persisted["events"][0]["event"] == "job_submitted"

    def test_publish_appends_event_for_current_latest_run(self):
        fake_redis = MagicMock()
        fake_collection = MagicMock()
        fake_collection.find_one.return_value = {"job_id": "abc123", "started_at": 1.0}
        pub = _make_publisher(
            redis_client=fake_redis,
            scrape_run_collection=fake_collection,
        )

        pub.publish(_make_event(event="job_started", status="running"))

        fake_collection.update_one.assert_called_once()
        update_doc = fake_collection.update_one.call_args.args[1]
        assert update_doc["$inc"] == {"event_count": 1}
        assert update_doc["$push"]["events"]["$slice"] == -_MAX_PERSISTED_SCRAPE_EVENTS
        assert update_doc["$set"]["status"] == "running"

    def test_publish_ignores_event_for_stale_job(self):
        fake_redis = MagicMock()
        fake_collection = MagicMock()
        fake_collection.find_one.return_value = {
            "job_id": "other-job",
            "started_at": 1.0,
            "status": "pending",
        }
        pub = _make_publisher(
            redis_client=fake_redis,
            scrape_run_collection=fake_collection,
        )

        pub.publish(_make_event(event="source_listing_collected", status="pending"))

        fake_collection.update_one.assert_not_called()
        fake_collection.replace_one.assert_not_called()

    def test_publish_replaces_stale_latest_run_when_active_job_resumes(self):
        fake_redis = MagicMock()
        fake_collection = MagicMock()
        fake_collection.find_one.return_value = {
            "job_id": "other-job",
            "started_at": 1.0,
            "status": "pending",
        }
        pub = _make_publisher(
            redis_client=fake_redis,
            scrape_run_collection=fake_collection,
        )

        pub.publish(_make_event(event="job_started", status="running"))

        fake_collection.replace_one.assert_called_once()
        persisted = fake_collection.replace_one.call_args.args[1]
        assert persisted["job_id"] == "abc123"
        assert persisted["status"] == "running"
        assert persisted["events"][0]["event"] == "job_started"

    def test_get_latest_scrape_run_sanitizes_document(self):
        fake_collection = MagicMock()
        fake_collection.find_one.return_value = {
            "job_id": "abc123",
            "status": "completed",
            "source": None,
            "trigger_type": "refresh",
            "started_at": 1.0,
            "updated_at": 2.0,
            "event_count": 99,
            "events": [
                {
                    "event": "job_completed",
                    "message": "done",
                    "timestamp": 2.0,
                    "job_id": "abc123",
                    "details": {"count": 5},
                    "extra": "ignored",
                }
            ],
        }

        with patch(
            "app.services.scrape_events._get_scrape_run_collection",
            return_value=fake_collection,
        ):
            latest_run = get_latest_scrape_run()

        assert latest_run is not None
        assert latest_run["event_count"] == 1
        assert latest_run["events"][0]["event"] == "job_completed"
        assert latest_run["events"][0]["details"] == {"count": 5}




def _make_fields(job_id: str = "abc", event: str = "job_submitted") -> dict:
    return {
        "event": event, "message": "test", "job_id": job_id,
        "source": "", "trigger_type": "manual", "status": "pending",
        "attempt_count": "", "timestamp": "1.0", "details": "{}",
    }


class TestScrapeEventReader:

    def test_stream_yields_message_and_advances_cursor(self):
        reader = ScrapeEventReader(
            redis_url="redis://localhost:6379/0",
            heartbeat_seconds=9999,
        )

        msg_id = "1680000000000-0"
        call_count = 0

        async def _fake_xread(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [("pulse:scrape:events:v1", [(msg_id, _make_fields())])]
            raise asyncio.CancelledError()

        fake_redis = MagicMock()
        fake_redis.xread = _fake_xread

        async def fake_aclose():
            pass

        fake_redis.aclose = fake_aclose

        results: list[tuple[str, dict]] = []

        async def _run():
            with patch("app.services.scrape_events.aioredis.from_url", return_value=fake_redis):
                async for mid, flds in reader.stream(last_id="$"):
                    if mid == _HEARTBEAT_SENTINEL:
                        continue
                    results.append((mid, flds))
                    break

        asyncio.run(_run())

        assert len(results) == 1
        assert results[0][0] == msg_id
        assert results[0][1]["event"] == "job_submitted"

    def test_stream_filters_by_job_id(self):
        reader = ScrapeEventReader(
            redis_url="redis://localhost:6379/0",
            heartbeat_seconds=9999,
        )

        batch = [
            ("1-0", _make_fields(job_id="other_job")),
            ("2-0", _make_fields(job_id="target_job")),
        ]

        call_count = 0

        async def _fake_xread(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [("pulse:scrape:events:v1", batch)]
            raise asyncio.CancelledError()

        fake_redis = MagicMock()
        fake_redis.xread = _fake_xread

        async def fake_aclose():
            pass

        fake_redis.aclose = fake_aclose

        results = []

        async def _run():
            with patch("app.services.scrape_events.aioredis.from_url", return_value=fake_redis):
                async for mid, flds in reader.stream(last_id="$", job_id_filter="target_job"):
                    if mid == _HEARTBEAT_SENTINEL:
                        continue
                    results.append((mid, flds))
                    break

        asyncio.run(_run())

        assert len(results) == 1
        assert results[0][1]["job_id"] == "target_job"

    def test_stream_creates_new_client_after_transient_error(self):
      
        reader = ScrapeEventReader(
            redis_url="redis://localhost:6379/0",
            heartbeat_seconds=9999,
        )

        msg_id = "9999-0"
        created_clients: list[MagicMock] = []

        def _make_client(client_index: int):
            client = MagicMock(name=f"redis_client_{client_index}")
            call_n = [0]

            async def _xread(*args, **kwargs):
                call_n[0] += 1
                if client_index == 0:
                    raise ConnectionError("transient blip on first client")
                if call_n[0] == 1:
                    return [("pulse:scrape:events:v1", [(msg_id, _make_fields(event="job_completed"))])]
                raise asyncio.CancelledError()

            async def _aclose():
                pass

            client.xread = _xread
            client.aclose = _aclose
            created_clients.append(client)
            return client

        def fake_create_client(self_reader):
            return _make_client(len(created_clients))

        results = []

        async def _run():
            with patch.object(ScrapeEventReader, "_create_client", fake_create_client):
                with patch("asyncio.sleep", return_value=None):
                    async for mid, flds in reader.stream(last_id="$"):
                        if mid == _HEARTBEAT_SENTINEL:
                            continue
                        results.append((mid, flds))
                        break

        asyncio.run(_run())

        assert len(created_clients) == 2
        assert created_clients[0] is not created_clients[1]
        assert len(results) == 1
        assert results[0][0] == msg_id
        assert results[0][1]["event"] == "job_completed"

    def test_stream_resets_cursor_after_max_consecutive_errors(self):
        reader = ScrapeEventReader(
            redis_url="redis://localhost:6379/0",
            heartbeat_seconds=9999,
        )
        reader._MAX_CONSECUTIVE_ERRORS = 3  # speed up test

        msg_id = "after-reset-0"
        call_count = 0
        xread_ids: list[str] = []

        async def _fake_xread(*args, **kwargs):
            nonlocal call_count
            streams = kwargs.get("streams") or (args[0] if args else {})
            for v in streams.values():
                xread_ids.append(v)
            call_count += 1
            # First 3 calls: fail  →  triggers cursor reset to "$"
            if call_count <= 3:
                raise RuntimeError("persistent bad-id error")
            # 4th call (after reset): succeed
            if call_count == 4:
                return [("pulse:scrape:events:v1", [(msg_id, _make_fields())])]
            raise asyncio.CancelledError()

        created_clients: list = []

        def _make_fresh_client(self_reader):
            c = MagicMock()
            c.xread = _fake_xread

            async def _aclose():
                pass

            c.aclose = _aclose
            created_clients.append(c)
            return c

        results = []

        async def _run():
            with patch.object(ScrapeEventReader, "_create_client", _make_fresh_client):
                with patch("asyncio.sleep", return_value=None):
                    async for mid, flds in reader.stream(last_id="bad-id-999"):
                        if mid == _HEARTBEAT_SENTINEL:
                            continue
                        results.append((mid, flds))
                        break

        asyncio.run(_run())

        assert "$" in xread_ids, f"Expected '$' in xread stream IDs after reset, got {xread_ids}"
        assert len(results) == 1
        assert results[0][0] == msg_id
