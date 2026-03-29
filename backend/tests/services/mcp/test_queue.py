from unittest.mock import MagicMock

from app.services.mcp.queue import WriteQueue
from app.services.mcp.schemas import NewsWriteRequest


def _req(url="https://a.com"):
    return NewsWriteRequest(title="Test", url=url, source="a.com")


def test_requeue_increments_attempt():
    q = WriteQueue(10, 3)
    q.enqueue(_req())
    item = q.dequeue_batch(1)[0]
    assert q.requeue(item, "error") is True
    item2 = q.dequeue_batch(1)[0]
    assert item2.attempt_count == 1


def test_max_retries_returns_false():
    q = WriteQueue(10, 3)
    q.enqueue(_req())
    item = q.dequeue_batch(1)[0]
    item.attempt_count = 3
    assert q.requeue(item, "still failing") is False


def test_empty_queue():
    q = WriteQueue(10, 3)
    assert q.is_empty() is True
    assert q.dequeue_batch(5) == []
    
def test_queue_full_returns_false():
    q = WriteQueue(0, 3)
    assert q.enqueue(_req()) is False


def test_queue_does_not_fall_back_to_memory_when_disabled():
    class FailingRedis:
        def ping(self):
            raise RuntimeError("redis down")

    import app.services.mcp.queue as queue_module

    original_available = queue_module._REDIS_AVAILABLE
    queue_module._REDIS_AVAILABLE = True

    original_from_url = getattr(queue_module, "redis_lib").from_url
    getattr(queue_module, "redis_lib").from_url = lambda *args, **kwargs: FailingRedis()

    try:
        q = WriteQueue(
            10,
            3,
            redis_url="redis://example:6379/0",
            allow_memory_fallback=False,
        )

        assert q.enqueue(_req()) is False
        assert q.dequeue_batch(1) == []
        assert q.size == 0
    finally:
        queue_module._REDIS_AVAILABLE = original_available
        getattr(queue_module, "redis_lib").from_url = original_from_url


def test_queue_reconnects_after_runtime_redis_failure():
    import app.services.mcp.queue as queue_module

    first_client = MagicMock()
    first_client.ping.return_value = True
    first_client.llen.side_effect = RuntimeError("redis down")

    second_client = MagicMock()
    second_client.ping.return_value = True
    second_client.llen.return_value = 0
    second_client.rpush.return_value = 1

    clients = iter([first_client, second_client])

    original_available = queue_module._REDIS_AVAILABLE
    queue_module._REDIS_AVAILABLE = True
    original_from_url = getattr(queue_module, "redis_lib").from_url
    getattr(queue_module, "redis_lib").from_url = lambda *args, **kwargs: next(clients)

    try:
        q = WriteQueue(
            10,
            3,
            redis_url="redis://example:6379/0",
            allow_memory_fallback=False,
        )

        assert q.enqueue(_req()) is False
        assert q.enqueue(_req("https://b.com")) is True
    finally:
        queue_module._REDIS_AVAILABLE = original_available
        getattr(queue_module, "redis_lib").from_url = original_from_url
