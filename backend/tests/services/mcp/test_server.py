from unittest.mock import MagicMock, patch

from app.services.mcp.config import MCPConfig
from app.services.mcp.server import create_write_services


def _cfg() -> MCPConfig:
    return MCPConfig(
        redis_url="redis://localhost:6379/0",
        mongo_url="mongodb://localhost:27017",
        mongo_db="kocaeli_news",
        lease_ttl_seconds=300,
        idempotency_ttl_seconds=86400,
        max_queue_size=10,
        max_queue_retries=3,
        fail_closed=True,
        worker_id="test-worker",
    )


@patch("app.services.mcp.server.MongoClient")
def test_create_write_services_passes_real_mongo_client(mock_mongo_client):
    fake_client = MagicMock()
    fake_client.admin.command.return_value = {"ok": 1}
    mock_mongo_client.return_value = fake_client

    write_service, lease = create_write_services(config=_cfg())

    assert write_service._mongo is fake_client


@patch("app.services.mcp.server.MongoClient")
def test_create_write_services_keeps_client_when_ping_fails(mock_mongo_client):
    fake_client = MagicMock()
    fake_client.admin.command.side_effect = RuntimeError("mongo down")
    mock_mongo_client.return_value = fake_client

    write_service, lease = create_write_services(config=_cfg())

    assert write_service._mongo is fake_client


@patch("app.services.mcp.server.MongoClient")
def test_create_write_services_returns_lease(mock_mongo_client):
    fake_client = MagicMock()
    fake_client.admin.command.return_value = {"ok": 1}
    mock_mongo_client.return_value = fake_client

    write_service, lease = create_write_services(config=_cfg())

    assert lease is not None
    assert write_service is not None
