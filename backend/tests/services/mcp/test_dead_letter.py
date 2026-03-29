from unittest.mock import MagicMock

from app.services.mcp.dead_letter import DeadLetterStore
from app.services.mcp.schemas import NewsWriteRequest


def _req(url="https://example.com/a"):
    return NewsWriteRequest(title="Test", url=url, source="example.com")


def test_add_increments_size():
    store = DeadLetterStore()
    store.add(_req(), "mongo down", attempt_count=1)

    assert store.size == 1
    items = store.get_all()
    assert len(items) == 1
    assert items[0].final_error == "mongo down"
    assert items[0].attempt_count == 1


def test_max_size_evicts_oldest():
    store = DeadLetterStore()
    store._MAX_SIZE = 2

    store.add(_req("https://example.com/1"), "e1", attempt_count=1)
    store.add(_req("https://example.com/2"), "e2", attempt_count=2)
    store.add(_req("https://example.com/3"), "e3", attempt_count=3)

    items = store.get_all()
    assert store.size == 2
    assert items[0].request.url == "https://example.com/2"
    assert items[1].request.url == "https://example.com/3"


def test_dead_letter_store_reconnects_after_runtime_redis_failure(monkeypatch):
    import app.services.mcp.dead_letter as dead_letter_module

    first_client = MagicMock()
    first_client.ping.return_value = True
    first_client.llen.side_effect = RuntimeError("redis down")

    second_client = MagicMock()
    second_client.ping.return_value = True
    second_client.llen.return_value = 7

    clients = iter([first_client, second_client])

    original_available = dead_letter_module._REDIS_AVAILABLE
    dead_letter_module._REDIS_AVAILABLE = True
    original_from_url = getattr(dead_letter_module, "redis_lib").from_url
    getattr(dead_letter_module, "redis_lib").from_url = lambda *args, **kwargs: next(clients)

    try:
        store = DeadLetterStore(redis_url="redis://example:6379/0")

        assert store.size == 0
        assert store.size == 7
    finally:
        dead_letter_module._REDIS_AVAILABLE = original_available
        getattr(dead_letter_module, "redis_lib").from_url = original_from_url
