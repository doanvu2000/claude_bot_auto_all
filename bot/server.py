"""WebSocket server with agent authentication, registration, and heartbeat monitoring.

The bot hosts this server. Agents connect outbound through NAT and authenticate
with a shared secret. Registered agents are tracked by machine_name and monitored
via heartbeat ping/pong.
"""
import asyncio
import signal
import time
from dataclasses import dataclass, field

from loguru import logger
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from bot.config import BotConfig
from shared.protocol import (
    AckMessage,
    DisconnectMessage,
    ErrorMessage,
    HeartbeatPing,
    HeartbeatPong,
    RegisterMessage,
    parse_message,
)


@dataclass
class AgentInfo:
    """Tracked state for a connected agent."""
    websocket: ServerConnection
    machine_name: str
    platform: str
    last_pong: float = field(default_factory=time.time)


class AgentManager:
    """Manages WebSocket connections from agents.

    Handles authentication via shared secret, tracks agents by machine_name,
    and monitors health via heartbeat ping/pong.
    """

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.agents: dict[str, AgentInfo] = {}

    async def handler(self, websocket: ServerConnection) -> None:
        """Main per-connection handler. Authenticates, then processes messages."""
        machine_name = await self._authenticate(websocket)
        if machine_name is None:
            return
        try:
            await self._handle_agent(websocket, machine_name)
        except ConnectionClosed:
            logger.debug(f"Connection closed for agent: {machine_name}")
        finally:
            self._remove_agent(machine_name)

    async def _authenticate(self, websocket: ServerConnection) -> str | None:
        """Authenticate an incoming connection. Returns machine_name or None."""
        try:
            raw = await asyncio.wait_for(
                websocket.recv(), timeout=self.config.registration_timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Registration timeout -- closing connection")
            await websocket.close(1008, "Registration timeout")
            return None
        except ConnectionClosed:
            return None

        try:
            msg = parse_message(raw)
        except Exception:
            await self._send_error(websocket, "invalid_message")
            return None

        if not isinstance(msg, RegisterMessage):
            await self._send_error(websocket, "expected_register", request_id=msg.request_id)
            return None

        if msg.secret != self.config.shared_secret:
            await self._send_error(websocket, "auth_failed", request_id=msg.request_id)
            return None

        if msg.machine_name in self.agents:
            await self._send_error(websocket, "machine_name_taken", request_id=msg.request_id)
            return None

        # Authentication successful -- register the agent
        self.agents[msg.machine_name] = AgentInfo(
            websocket=websocket,
            machine_name=msg.machine_name,
            platform=msg.platform,
            last_pong=time.time(),
        )
        ack = AckMessage(request_id=msg.request_id)
        await websocket.send(ack.model_dump_json())
        logger.info(f"Agent registered: {msg.machine_name} ({msg.platform})")
        return msg.machine_name

    async def _handle_agent(self, websocket: ServerConnection, machine_name: str) -> None:
        """Process messages from a registered agent."""
        async for raw in websocket:
            try:
                msg = parse_message(raw)
            except Exception:
                logger.warning(f"Invalid message from {machine_name}, ignoring")
                continue

            if isinstance(msg, HeartbeatPong):
                if machine_name in self.agents:
                    self.agents[machine_name].last_pong = time.time()
            elif isinstance(msg, DisconnectMessage):
                logger.info(f"Agent graceful disconnect: {machine_name}")
                break
            else:
                logger.debug(f"Unhandled message type from {machine_name}: {type(msg).__name__}")

    def _remove_agent(self, machine_name: str) -> None:
        """Remove agent from tracked dict."""
        if machine_name in self.agents:
            del self.agents[machine_name]
            logger.info(f"Agent disconnected: {machine_name}")

    async def _heartbeat_loop(self) -> None:
        """Periodically ping agents and remove unresponsive ones."""
        while True:
            await asyncio.sleep(self.config.heartbeat_interval)
            now = time.time()
            dead: list[str] = []

            for name, agent in list(self.agents.items()):
                if now - agent.last_pong > self.config.heartbeat_timeout:
                    dead.append(name)
                else:
                    try:
                        ping = HeartbeatPing()
                        await agent.websocket.send(ping.model_dump_json())
                    except ConnectionClosed:
                        dead.append(name)

            for name in dead:
                agent = self.agents.get(name)
                if agent:
                    logger.warning(f"Agent heartbeat timeout: {name}")
                    try:
                        await agent.websocket.close(1008, "Heartbeat timeout")
                    except Exception:
                        pass
                    self._remove_agent(name)

    async def _send_error(
        self, websocket: ServerConnection, reason: str, request_id: str | None = None
    ) -> None:
        """Send an ErrorMessage and close the connection."""
        kwargs = {"reason": reason}
        if request_id:
            kwargs["request_id"] = request_id
        error = ErrorMessage(**kwargs)
        try:
            await websocket.send(error.model_dump_json())
            await websocket.close(1008, reason)
        except ConnectionClosed:
            pass


async def start_server(config: BotConfig) -> None:
    """Start the WebSocket server with agent management.

    Runs until SIGINT or SIGTERM is received.
    """
    manager = AgentManager(config)
    shutdown_event = asyncio.Event()

    def _signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    heartbeat_task = asyncio.create_task(manager._heartbeat_loop())
    logger.info(f"WebSocket server starting on ws://{config.ws_host}:{config.ws_port}")

    async with serve(manager.handler, config.ws_host, config.ws_port):
        await shutdown_event.wait()

    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass

    logger.info("WebSocket server shut down")
