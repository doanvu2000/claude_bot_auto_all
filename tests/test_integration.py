"""End-to-end integration tests: bot server + agent client full handshake.

These tests start a real bot server and a real agent client, verifying
they work together end-to-end without mocking the transport layer.
"""
import asyncio
import sys

import pytest
from websockets.asyncio.server import serve

from agent.client import AgentClient
from agent.config import AgentConfig
from bot.config import BotConfig
from bot.server import AgentManager


def _make_client(port, secret, machine_name="test-machine", **kwargs):
    """Create an AgentClient with test-friendly defaults."""
    config = AgentConfig(
        shared_secret=secret,
        bot_url=f"ws://127.0.0.1:{port}",
        machine_name=machine_name,
    )
    defaults = dict(base_delay=0.1, max_delay=1.0, jitter_max=0.0)
    defaults.update(kwargs)
    return AgentClient(config, **defaults)


async def _wait_for_agent(manager, name, timeout=5.0):
    """Wait until agent appears in manager.agents, or raise TimeoutError."""
    elapsed = 0.0
    while elapsed < timeout:
        if name in manager.agents:
            return
        await asyncio.sleep(0.05)
        elapsed += 0.05
    raise TimeoutError(f"Agent '{name}' did not register within {timeout}s")


async def _wait_for_agent_gone(manager, name, timeout=5.0):
    """Wait until agent disappears from manager.agents."""
    elapsed = 0.0
    while elapsed < timeout:
        if name not in manager.agents:
            return
        await asyncio.sleep(0.05)
        elapsed += 0.05
    raise TimeoutError(f"Agent '{name}' did not disconnect within {timeout}s")


@pytest.mark.asyncio
async def test_full_handshake_flow(bot_config):
    """Bot server and agent client complete registration, then agent disconnects gracefully."""
    manager = AgentManager(bot_config)
    heartbeat_task = asyncio.create_task(manager._heartbeat_loop())
    server = await serve(manager.handler, bot_config.ws_host, bot_config.ws_port)

    client = _make_client(bot_config.ws_port, bot_config.shared_secret)
    agent_task = asyncio.create_task(client.run())

    try:
        await asyncio.wait_for(_wait_for_agent(manager, "test-machine"), timeout=5)

        # Verify registration metadata
        assert "test-machine" in manager.agents
        info = manager.agents["test-machine"]
        assert info.platform == sys.platform
        assert info.machine_name == "test-machine"

        # Graceful shutdown
        await client.stop()
        await asyncio.wait_for(_wait_for_agent_gone(manager, "test-machine"), timeout=5)
        assert "test-machine" not in manager.agents
    finally:
        agent_task.cancel()
        heartbeat_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_heartbeat_keeps_connection_alive(free_port, test_secret):
    """Heartbeat ping/pong keeps agent alive through multiple cycles."""
    config = BotConfig(
        shared_secret=test_secret,
        ws_host="127.0.0.1",
        ws_port=free_port,
        heartbeat_interval=0.5,  # Fast heartbeat for test
        heartbeat_timeout=2,
        registration_timeout=2,
    )
    manager = AgentManager(config)
    heartbeat_task = asyncio.create_task(manager._heartbeat_loop())
    server = await serve(manager.handler, config.ws_host, config.ws_port)

    client = _make_client(free_port, test_secret)
    agent_task = asyncio.create_task(client.run())

    try:
        await asyncio.wait_for(_wait_for_agent(manager, "test-machine"), timeout=5)

        # Wait through several heartbeat cycles
        await asyncio.sleep(3.0)

        # Agent should still be alive (heartbeat kept it alive)
        assert "test-machine" in manager.agents
    finally:
        await client.stop()
        agent_task.cancel()
        heartbeat_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_agent_reconnects_after_server_restart(free_port, test_secret):
    """Agent reconnects and re-registers after server restarts on same port."""
    bot_cfg = BotConfig(
        shared_secret=test_secret,
        ws_host="127.0.0.1",
        ws_port=free_port,
        heartbeat_interval=60,  # Disable heartbeat for this test
        heartbeat_timeout=120,
        registration_timeout=2,
    )

    # Start first server
    manager1 = AgentManager(bot_cfg)
    server1 = await serve(manager1.handler, bot_cfg.ws_host, bot_cfg.ws_port)

    client = _make_client(free_port, test_secret, base_delay=0.2, max_delay=1.0)
    agent_task = asyncio.create_task(client.run())

    try:
        await asyncio.wait_for(_wait_for_agent(manager1, "test-machine"), timeout=5)
        assert "test-machine" in manager1.agents

        # Stop first server (agent will detect disconnect)
        server1.close()
        await server1.wait_closed()

        # Brief pause for agent to detect disconnect
        await asyncio.sleep(0.5)

        # Start NEW server on same port
        manager2 = AgentManager(bot_cfg)
        server2 = await serve(manager2.handler, bot_cfg.ws_host, bot_cfg.ws_port)

        # Wait for agent to reconnect to new server
        await asyncio.wait_for(_wait_for_agent(manager2, "test-machine"), timeout=10)
        assert "test-machine" in manager2.agents

        server2.close()
        await server2.wait_closed()
    finally:
        await client.stop()
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_wrong_secret_rejected(bot_config):
    """Agent with wrong secret is rejected and does not appear in manager."""
    manager = AgentManager(bot_config)
    server = await serve(manager.handler, bot_config.ws_host, bot_config.ws_port)

    client = _make_client(
        bot_config.ws_port,
        secret="wrong-secret-xyz",
        base_delay=0.1,
        max_delay=0.5,
    )
    agent_task = asyncio.create_task(client.run())

    try:
        # Wait some time -- agent should never appear
        await asyncio.sleep(2.0)
        assert "test-machine" not in manager.agents
    finally:
        await client.stop()
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass
        server.close()
        await server.wait_closed()
