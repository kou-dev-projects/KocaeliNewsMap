from app.services.geocoding.queue import GeocodingQueue
from app.services.geocoding.schemas import GeocodingInput


def test_enqueue_and_dequeue():
    q = GeocodingQueue()
    inp = GeocodingInput(address="İzmit")
    q.enqueue(inp, "rate_limit")
    assert q.size == 1
    batch = q.dequeue_batch(10)
    assert len(batch) == 1
    assert q.size == 0

def test_requeue_increments_attempt():
    q = GeocodingQueue()
    inp = GeocodingInput(address="Test")
    q.enqueue(inp, "rate_limit")
    item = q.dequeue_batch(1)[0]
    q.requeue(item, "still failing")
    assert q.size == 1
    item2 = q.dequeue_batch(1)[0]
    assert item2.attempt_count == 1

def test_max_retries_drops_item():
    q = GeocodingQueue()
    inp = GeocodingInput(address="Test")
    q.enqueue(inp, "rate_limit")
    item = q.dequeue_batch(1)[0]
    for _ in range(3):
        item.attempt_count += 1
    q.requeue(item, "still failing")
    assert q.size == 0   # max retries aşıldı, drop edildi


def test_enqueue_returns_false_when_full():
    q = GeocodingQueue()
    q._MAX_SIZE = 0
    assert q.enqueue(GeocodingInput(address="İzmit"), "rate_limit") is False
