import pytest
from unittest.mock import MagicMock, patch
from app.services.mcp.lease import SourceLease


@pytest.fixture
def lease():
    # Redis mock ile
    with patch("app.services.mcp.lease._REDIS_AVAILABLE", True):
        with patch("redis.from_url") as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            svc = SourceLease("redis://localhost", 300)
            svc._client = mock_client
            yield svc, mock_client


def test_acquire_success(lease):
    svc, mock_client = lease
    mock_client.set.return_value = True
    result = svc.acquire("cagdaskocaeli.com.tr", "worker-1")
    assert result is True


def test_acquire_already_held(lease):
    svc, mock_client = lease
    mock_client.set.return_value = None   # NX başarısız
    mock_client.get.return_value = "worker-2"
    result = svc.acquire("cagdaskocaeli.com.tr", "worker-1")
    assert result is False


def test_release_success(lease):
    svc, mock_client = lease
    mock_client.eval.return_value = 1
    result = svc.release("cagdaskocaeli.com.tr", "worker-1")
    assert result is True


def test_release_not_owner(lease):
    svc, mock_client = lease
    mock_client.eval.return_value = 0   # başkasının kilidi
    result = svc.release("cagdaskocaeli.com.tr", "worker-1")
    assert result is False


def test_no_redis_acquire_returns_false():
    svc = SourceLease("redis://localhost", 300)
    svc._client = None
    assert svc.acquire("source", "worker") is False


def test_is_held(lease):
    svc, mock_client = lease
    mock_client.exists.return_value = 1
    assert svc.is_held("cagdaskocaeli.com.tr") is True


def test_lease_reconnects_after_runtime_redis_failure(monkeypatch):
    first_client = MagicMock()
    first_client.ping.return_value = True
    first_client.exists.side_effect = RuntimeError("redis down")

    second_client = MagicMock()
    second_client.ping.return_value = True
    second_client.exists.return_value = 1

    clients = iter([first_client, second_client])

    monkeypatch.setattr("app.services.mcp.lease._REDIS_AVAILABLE", True)
    monkeypatch.setattr("redis.from_url", lambda *args, **kwargs: next(clients))

    svc = SourceLease("redis://localhost", 300)

    assert svc.is_held("source") is False
    assert svc.is_held("source") is True
