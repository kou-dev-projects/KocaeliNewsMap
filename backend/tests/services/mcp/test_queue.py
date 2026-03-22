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