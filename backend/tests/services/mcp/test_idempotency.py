import pytest
from unittest.mock import MagicMock, patch
from app.services.mcp.idempotency import IdempotencyStore


@pytest.fixture
def store():
    with patch("app.services.mcp.idempotency._REDIS_AVAILABLE", True):
        with patch("redis.from_url") as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            svc = IdempotencyStore("redis://localhost", 86400)
            svc._client = mock_client
            yield svc, mock_client


def test_not_duplicate_initially(store):
    svc, mock_client = store
    mock_client.exists.return_value = 0
    assert svc.is_duplicate("abc123") is False


def test_is_duplicate_after_mark(store):
    svc, mock_client = store
    mock_client.exists.return_value = 1
    assert svc.is_duplicate("abc123") is True


def test_mark_processed_calls_setex(store):
    svc, mock_client = store
    svc.mark_processed("abc123", "news_001")
    mock_client.setex.assert_called_once()


def test_no_redis_not_duplicate():
    svc = IdempotencyStore("redis://localhost", 86400)
    svc._client = None
    assert svc.is_duplicate("abc123") is False


def test_get_existing_id(store):
    svc, mock_client = store
    mock_client.get.return_value = "news_001"
    assert svc.get_existing_id("abc123") == "news_001"