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
