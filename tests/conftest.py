"""Shared test fixtures."""
import os
import json
import socket
import tempfile
import pytest
import pytest_asyncio

from bot.config import BotConfig


@pytest.fixture
def tmp_env_file(tmp_path):
    """Create a temporary .env file with test values."""
    env_file = tmp_path / ".env"
    env_file.write_text("SHARED_SECRET=test-secret-123\nMACHINE_NAME=test-machine\nBOT_URL=ws://localhost:9999\n")
    return str(env_file)


@pytest.fixture
def tmp_config_file(tmp_path):
    """Create a temporary config.json with test values."""
    config = {
        "websocket": {
            "host": "127.0.0.1",
            "port": 9999
        },
        "heartbeat": {
            "interval_seconds": 10,
            "timeout_seconds": 20
        },
        "auth": {
            "registration_timeout_seconds": 5
        },
        "logging": {
            "level": "DEBUG",
            "file": "logs/test.log",
            "rotation": "5 MB",
            "retention": "3 days"
        }
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    return str(config_file)


@pytest.fixture
def free_port():
    """Find an available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture
def test_secret():
    """Shared secret for tests."""
    return "test-secret-123"


@pytest.fixture
def bot_config(free_port, test_secret):
    """BotConfig with fast timeouts for testing."""
    return BotConfig(
        shared_secret=test_secret,
        ws_host="127.0.0.1",
        ws_port=free_port,
        heartbeat_interval=1,
        heartbeat_timeout=3,
        registration_timeout=2,
    )


@pytest_asyncio.fixture
async def ws_server(bot_config):
    """Start a WebSocket server with AgentManager, yield (manager, port), then shut down."""
    from bot.server import AgentManager
    from websockets.asyncio.server import serve
    import asyncio

    manager = AgentManager(bot_config)
    server = await serve(manager.handler, bot_config.ws_host, bot_config.ws_port)
    heartbeat_task = asyncio.create_task(manager._heartbeat_loop())
    yield manager, bot_config.ws_port
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    server.close()
    await server.wait_closed()


@pytest.fixture
def ws_uri(ws_server):
    """WebSocket URI for test client connections."""
    _, port = ws_server
    return f"ws://127.0.0.1:{port}"
