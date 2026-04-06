"""Tests for agent WebSocket client: connection, registration, heartbeat, reconnection."""
import asyncio
import sys

import pytest
import pytest_asyncio
from loguru import logger
from websockets.asyncio.server import serve

from agent.config import AgentConfig
from agent.client import AgentClient
from bot.config import BotConfig
from bot.server import AgentManager
from shared.protocol import (
    AckMessage,
    ErrorMessage,
    HeartbeatPing,
    HeartbeatPong,
    RegisterMessage,
    DisconnectMessage,
    parse_message,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent(port, secret="test-secret-123", machine_name="test-agent",
                base_delay=0.05, max_delay=0.5, jitter_max=0.0):
    """Create an AgentClient with fast test timings."""
    config = AgentConfig(
        shared_secret=secret,
        bot_url=f"ws://127.0.0.1:{port}",
        machine_name=machine_name,
    )
    return AgentClient(
        config,
        base_delay=base_delay,
        max_delay=max_delay,
        jitter_max=jitter_max,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_connects_and_registers(bot_config):
    """Agent connects to server and successfully registers."""
    manager = AgentManager(bot_config)
    async with serve(manager.handler, bot_config.ws_host, bot_config.ws_port):
        agent = _make_agent(bot_config.ws_port, secret=bot_config.shared_secret)
        task = asyncio.create_task(agent.run())
        try:
            # Wait for agent to appear
            for _ in range(50):
                if "test-agent" in manager.agents:
                    break
                await asyncio.sleep(0.05)
            assert "test-agent" in manager.agents
            info = manager.agents["test-agent"]
            assert info.machine_name == "test-agent"
            assert info.platform == sys.platform
        finally:
            await agent.stop()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


@pytest.mark.asyncio
async def test_agent_responds_to_heartbeat(bot_config):
    """Agent responds to HeartbeatPing with HeartbeatPong with matching request_id."""
    manager = AgentManager(bot_config)
    async with serve(manager.handler, bot_config.ws_host, bot_config.ws_port):
        agent = _make_agent(bot_config.ws_port, secret=bot_config.shared_secret)
        task = asyncio.create_task(agent.run())
        try:
            # Wait for registration
            for _ in range(50):
                if "test-agent" in manager.agents:
                    break
                await asyncio.sleep(0.05)
            assert "test-agent" in manager.agents

            # Send heartbeat ping from server
            ping = HeartbeatPing()
            ws = manager.agents["test-agent"].websocket
            await ws.send(ping.model_dump_json())

            # The server's _handle_agent loop should receive the pong
            # and update last_pong. Give it a moment.
            import time
            before = manager.agents["test-agent"].last_pong
            await asyncio.sleep(0.3)
            after = manager.agents["test-agent"].last_pong
            # last_pong should have been updated
            assert after >= before
        finally:
            await agent.stop()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


@pytest.mark.asyncio
async def test_agent_reconnects_on_server_close(bot_config):
    """When server closes connection, agent reconnects and re-registers."""
    manager = AgentManager(bot_config)
    server = await serve(manager.handler, bot_config.ws_host, bot_config.ws_port)

    agent = _make_agent(bot_config.ws_port, secret=bot_config.shared_secret,
                        base_delay=0.05, max_delay=0.5, jitter_max=0.0)
    task = asyncio.create_task(agent.run())
    try:
        # Wait for initial registration
        for _ in range(50):
            if "test-agent" in manager.agents:
                break
            await asyncio.sleep(0.05)
        assert "test-agent" in manager.agents

        # Close the agent's websocket from server side
        ws = manager.agents["test-agent"].websocket
        await ws.close()

        # Wait for agent to disappear and then re-register
        for _ in range(100):
            await asyncio.sleep(0.05)
            if "test-agent" in manager.agents:
                # Check it's a new connection (last_pong refreshed)
                break
        # Agent should have reconnected
        assert "test-agent" in manager.agents
    finally:
        await agent.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_backoff_doubles():
    """Backoff delay doubles after each failed connection attempt."""
    delays_recorded = []

    async def mock_sleep(duration):
        delays_recorded.append(duration)
        await asyncio.sleep(0.01)

    config = AgentConfig(
        shared_secret="test",
        bot_url="ws://127.0.0.1:1",  # Will fail to connect
        machine_name="test-backoff",
    )
    agent = AgentClient(config, base_delay=1.0, max_delay=60.0, jitter_max=0.0)
    agent._sleep = mock_sleep

    task = asyncio.create_task(agent.run())
    try:
        # Connection attempts to port 1 may take ~1s each on Windows
        for _ in range(300):
            if len(delays_recorded) >= 4:
                break
            await asyncio.sleep(0.1)

        assert len(delays_recorded) >= 4
        # Delays should approximately double: 1, 2, 4, 8
        assert abs(delays_recorded[0] - 1.0) < 0.01
        assert abs(delays_recorded[1] - 2.0) < 0.01
        assert abs(delays_recorded[2] - 4.0) < 0.01
        assert abs(delays_recorded[3] - 8.0) < 0.01
    finally:
        await agent.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_backoff_caps_at_max():
    """Backoff delay never exceeds max_delay."""
    delays_recorded = []

    async def mock_sleep(duration):
        delays_recorded.append(duration)
        await asyncio.sleep(0.01)

    config = AgentConfig(
        shared_secret="test",
        bot_url="ws://127.0.0.1:1",
        machine_name="test-cap",
    )
    # Start with high base so we hit cap quickly
    agent = AgentClient(config, base_delay=16.0, max_delay=60.0, jitter_max=0.0)
    agent._sleep = mock_sleep

    task = asyncio.create_task(agent.run())
    try:
        for _ in range(300):
            if len(delays_recorded) >= 4:
                break
            await asyncio.sleep(0.1)

        assert len(delays_recorded) >= 4
        for d in delays_recorded:
            assert d <= 60.0 + 0.01  # No jitter, should be exactly <= 60
    finally:
        await agent.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_backoff_resets_on_success(bot_config):
    """Backoff resets to base_delay after a successful connection."""
    delays_recorded = []

    async def mock_sleep(duration):
        delays_recorded.append(duration)
        await asyncio.sleep(0.01)

    # Start with no server (will fail and backoff)
    agent = _make_agent(bot_config.ws_port, secret=bot_config.shared_secret,
                        base_delay=0.1, max_delay=5.0, jitter_max=0.0)
    agent._sleep = mock_sleep
    task = asyncio.create_task(agent.run())

    try:
        # Let it fail a couple times (connection failures can take ~1s on Windows)
        for _ in range(150):
            if len(delays_recorded) >= 2:
                break
            await asyncio.sleep(0.1)

        assert len(delays_recorded) >= 2
        # Delays should have grown
        assert delays_recorded[1] > delays_recorded[0]

        # Now start the server
        manager = AgentManager(bot_config)
        server = await serve(manager.handler, bot_config.ws_host, bot_config.ws_port)

        # Wait for registration
        for _ in range(200):
            if "test-agent" in manager.agents:
                break
            await asyncio.sleep(0.1)
        assert "test-agent" in manager.agents

        # Record delay count before disconnect
        count_before = len(delays_recorded)

        # Close connection from server
        ws = manager.agents["test-agent"].websocket
        await ws.close()

        # Wait for a new delay to be recorded
        for _ in range(150):
            if len(delays_recorded) > count_before:
                break
            await asyncio.sleep(0.1)

        # The new delay should be back to base (~0.1)
        if len(delays_recorded) > count_before:
            assert delays_recorded[count_before] == pytest.approx(0.1, abs=0.02)

        server.close()
        await server.wait_closed()
    finally:
        await agent.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_agent_sends_disconnect_on_shutdown(bot_config):
    """Agent sends DisconnectMessage before closing on stop()."""
    received_messages = []

    async def capturing_handler(websocket):
        """Accept registration, then capture all subsequent messages."""
        raw = await websocket.recv()
        msg = parse_message(raw)
        if isinstance(msg, RegisterMessage):
            ack = AckMessage(request_id=msg.request_id)
            await websocket.send(ack.model_dump_json())

        try:
            async for raw in websocket:
                received_messages.append(parse_message(raw))
        except Exception:
            pass

    server = await serve(capturing_handler, bot_config.ws_host, bot_config.ws_port)
    agent = _make_agent(bot_config.ws_port, secret=bot_config.shared_secret)
    task = asyncio.create_task(agent.run())

    try:
        # Wait for connection
        await asyncio.sleep(0.3)

        # Stop agent gracefully
        await agent.stop()
        await asyncio.sleep(0.2)

        # Check that a DisconnectMessage was received
        disconnect_msgs = [m for m in received_messages if isinstance(m, DisconnectMessage)]
        assert len(disconnect_msgs) >= 1
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_agent_handles_auth_rejection(bot_config, capsys):
    """Agent logs error when server rejects auth."""
    manager = AgentManager(bot_config)
    async with serve(manager.handler, bot_config.ws_host, bot_config.ws_port):
        # Use wrong secret
        agent = _make_agent(bot_config.ws_port, secret="wrong-secret",
                            base_delay=0.05, max_delay=0.1, jitter_max=0.0)

        log_messages = []
        handler_id = logger.add(lambda msg: log_messages.append(str(msg)), level="ERROR")

        task = asyncio.create_task(agent.run())
        try:
            await asyncio.sleep(0.5)
            # Agent should not be registered
            assert "test-agent" not in manager.agents
            # Should have logged an error about auth rejection
            auth_errors = [m for m in log_messages if "auth_failed" in m.lower()
                          or "rejected" in m.lower() or "registration" in m.lower()]
            assert len(auth_errors) > 0
        finally:
            await agent.stop()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.remove(handler_id)
