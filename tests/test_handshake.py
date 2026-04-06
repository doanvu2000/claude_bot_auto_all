"""Tests for WebSocket handshake: auth, registration, and edge cases."""
import asyncio
import json

import pytest
from websockets.asyncio.client import connect

from shared.protocol import (
    AckMessage,
    ErrorMessage,
    HeartbeatPing,
    RegisterMessage,
    parse_message,
)


def _register_json(secret: str, machine_name: str = "test-machine", platform: str = "win32") -> str:
    """Build a RegisterMessage JSON string."""
    return RegisterMessage(secret=secret, machine_name=machine_name, platform=platform).model_dump_json()


@pytest.mark.asyncio
async def test_auth_success(ws_server, ws_uri, test_secret):
    """Agent with correct secret registers and receives AckMessage."""
    manager, _ = ws_server
    msg = RegisterMessage(secret=test_secret, machine_name="machine-a", platform="win32")
    async with connect(ws_uri) as ws:
        await ws.send(msg.model_dump_json())
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        response = parse_message(raw)
        assert isinstance(response, AckMessage)
        assert response.request_id == msg.request_id


@pytest.mark.asyncio
async def test_auth_failure(ws_server, ws_uri):
    """Agent with wrong secret receives ErrorMessage and connection closes."""
    manager, _ = ws_server
    async with connect(ws_uri) as ws:
        await ws.send(_register_json(secret="wrong-secret"))
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        response = parse_message(raw)
        assert isinstance(response, ErrorMessage)
        assert response.reason == "auth_failed"
        # Connection should be closed by server
        with pytest.raises(Exception):
            await asyncio.wait_for(ws.recv(), timeout=2)


@pytest.mark.asyncio
async def test_non_register_first_message(ws_server, ws_uri):
    """Non-register message as first message receives error and connection closes."""
    manager, _ = ws_server
    ping = HeartbeatPing()
    async with connect(ws_uri) as ws:
        await ws.send(ping.model_dump_json())
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        response = parse_message(raw)
        assert isinstance(response, ErrorMessage)
        assert response.reason == "expected_register"
        with pytest.raises(Exception):
            await asyncio.wait_for(ws.recv(), timeout=2)


@pytest.mark.asyncio
async def test_malformed_json(ws_server, ws_uri):
    """Malformed JSON receives error and connection closes."""
    manager, _ = ws_server
    async with connect(ws_uri) as ws:
        await ws.send("not json{{")
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        response = parse_message(raw)
        assert isinstance(response, ErrorMessage)
        assert response.reason == "invalid_message"
        with pytest.raises(Exception):
            await asyncio.wait_for(ws.recv(), timeout=2)


@pytest.mark.asyncio
async def test_registration_timeout(ws_server, ws_uri, bot_config):
    """Client that sends nothing within registration_timeout gets disconnected."""
    manager, _ = ws_server
    async with connect(ws_uri) as ws:
        # Wait longer than registration_timeout (2s in test config)
        with pytest.raises(Exception):
            await asyncio.wait_for(ws.recv(), timeout=bot_config.registration_timeout + 2)


@pytest.mark.asyncio
async def test_duplicate_machine_name(ws_server, ws_uri, test_secret):
    """Second agent with same machine_name is rejected."""
    manager, _ = ws_server
    # Register first agent
    async with connect(ws_uri) as ws1:
        await ws1.send(_register_json(secret=test_secret, machine_name="machine-a"))
        raw = await asyncio.wait_for(ws1.recv(), timeout=5)
        assert isinstance(parse_message(raw), AckMessage)

        # Try to register second agent with same name
        async with connect(ws_uri) as ws2:
            await ws2.send(_register_json(secret=test_secret, machine_name="machine-a"))
            raw2 = await asyncio.wait_for(ws2.recv(), timeout=5)
            response = parse_message(raw2)
            assert isinstance(response, ErrorMessage)
            assert response.reason == "machine_name_taken"


@pytest.mark.asyncio
async def test_re_register_after_disconnect(ws_server, ws_uri, test_secret):
    """After disconnect, same machine_name can re-register."""
    manager, _ = ws_server
    # Register and disconnect
    async with connect(ws_uri) as ws1:
        await ws1.send(_register_json(secret=test_secret, machine_name="machine-a"))
        raw = await asyncio.wait_for(ws1.recv(), timeout=5)
        assert isinstance(parse_message(raw), AckMessage)
    # ws1 is now closed

    # Small delay for server to process disconnect
    await asyncio.sleep(0.2)

    # Re-register with same name
    async with connect(ws_uri) as ws2:
        await ws2.send(_register_json(secret=test_secret, machine_name="machine-a"))
        raw2 = await asyncio.wait_for(ws2.recv(), timeout=5)
        response = parse_message(raw2)
        assert isinstance(response, AckMessage)
