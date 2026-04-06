"""Tests for WebSocket server: connection, heartbeat, and lifecycle."""
import asyncio

import pytest
from websockets.asyncio.client import connect

from shared.protocol import (
    AckMessage,
    DisconnectMessage,
    HeartbeatPing,
    HeartbeatPong,
    RegisterMessage,
    parse_message,
)


def _register_json(secret: str, machine_name: str = "test-machine", platform: str = "win32") -> str:
    """Build a RegisterMessage JSON string."""
    return RegisterMessage(secret=secret, machine_name=machine_name, platform=platform).model_dump_json()


async def _register_agent(ws_uri: str, secret: str, machine_name: str):
    """Connect and register an agent, returning the open websocket."""
    ws = await connect(ws_uri)
    await ws.send(_register_json(secret=secret, machine_name=machine_name))
    raw = await asyncio.wait_for(ws.recv(), timeout=5)
    msg = parse_message(raw)
    assert isinstance(msg, AckMessage)
    return ws


@pytest.mark.asyncio
async def test_server_accepts_connection(ws_server, ws_uri):
    """Server accepts WebSocket connections."""
    manager, _ = ws_server
    async with connect(ws_uri) as ws:
        assert ws.protocol.state.name == "OPEN"


@pytest.mark.asyncio
async def test_heartbeat_ping_received(ws_server, ws_uri, test_secret, bot_config):
    """After registration, server sends HeartbeatPing within heartbeat interval."""
    manager, _ = ws_server
    ws = await _register_agent(ws_uri, test_secret, "machine-a")
    try:
        # Wait for heartbeat ping (interval is 1s in test config)
        raw = await asyncio.wait_for(ws.recv(), timeout=bot_config.heartbeat_interval + 2)
        msg = parse_message(raw)
        assert isinstance(msg, HeartbeatPing)
    finally:
        await ws.close()


@pytest.mark.asyncio
async def test_heartbeat_pong_keeps_alive(ws_server, ws_uri, test_secret, bot_config):
    """Responding to ping with pong keeps the connection alive."""
    manager, _ = ws_server
    ws = await _register_agent(ws_uri, test_secret, "machine-a")
    try:
        # Receive first ping and respond with pong
        raw = await asyncio.wait_for(ws.recv(), timeout=bot_config.heartbeat_interval + 2)
        msg = parse_message(raw)
        assert isinstance(msg, HeartbeatPing)
        await ws.send(HeartbeatPong().model_dump_json())

        # Should receive another ping (still alive)
        raw2 = await asyncio.wait_for(ws.recv(), timeout=bot_config.heartbeat_interval + 2)
        msg2 = parse_message(raw2)
        assert isinstance(msg2, HeartbeatPing)
    finally:
        await ws.close()


@pytest.mark.asyncio
async def test_heartbeat_timeout_removes_agent(ws_server, ws_uri, test_secret, bot_config):
    """Agent that does not respond to heartbeat pings is removed after timeout."""
    manager, _ = ws_server
    ws = await _register_agent(ws_uri, test_secret, "machine-a")
    try:
        # Receive ping but do NOT send pong
        raw = await asyncio.wait_for(ws.recv(), timeout=bot_config.heartbeat_interval + 2)
        assert isinstance(parse_message(raw), HeartbeatPing)

        # Wait for timeout -- connection should be closed and agent removed
        await asyncio.sleep(bot_config.heartbeat_timeout + 1)
        assert "machine-a" not in manager.agents
    finally:
        try:
            await ws.close()
        except Exception:
            pass  # May already be closed


@pytest.mark.asyncio
async def test_disconnect_message_removes_agent(ws_server, ws_uri, test_secret):
    """Agent sending DisconnectMessage is cleanly removed."""
    manager, _ = ws_server
    ws = await _register_agent(ws_uri, test_secret, "machine-a")
    assert "machine-a" in manager.agents

    await ws.send(DisconnectMessage().model_dump_json())
    await asyncio.sleep(0.3)  # Allow server to process
    assert "machine-a" not in manager.agents
    await ws.close()


@pytest.mark.asyncio
async def test_multiple_agents_independent(ws_server, ws_uri, test_secret):
    """Disconnecting one agent does not affect others."""
    manager, _ = ws_server
    ws1 = await _register_agent(ws_uri, test_secret, "machine-a")
    ws2 = await _register_agent(ws_uri, test_secret, "machine-b")
    assert "machine-a" in manager.agents
    assert "machine-b" in manager.agents

    # Disconnect machine-a
    await ws1.send(DisconnectMessage().model_dump_json())
    await asyncio.sleep(0.3)

    assert "machine-a" not in manager.agents
    assert "machine-b" in manager.agents

    await ws2.close()
