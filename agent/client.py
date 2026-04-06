"""WebSocket client for the agent with reconnection, heartbeat, and graceful shutdown.

The agent connects outbound to the bot's WebSocket server (NAT-friendly),
authenticates via shared secret, and maintains a persistent connection with
automatic recovery from network failures using exponential backoff.
"""
import asyncio
import random
import sys

from loguru import logger
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from agent.config import AgentConfig
from shared.protocol import (
    AckMessage,
    DisconnectMessage,
    ErrorMessage,
    HeartbeatPing,
    HeartbeatPong,
    RegisterMessage,
    parse_message,
)


class AgentClient:
    """WebSocket client that connects to the bot server and maintains a persistent connection.

    Handles registration, heartbeat responses, graceful shutdown,
    and exponential backoff reconnection on network failures.
    """

    def __init__(
        self,
        config: AgentConfig,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter_max: float = 1.0,
    ) -> None:
        self.config = config
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_max = jitter_max
        self._running = True
        self._websocket = None
        self._sleep = asyncio.sleep  # Injectable for testing

    async def run(self) -> None:
        """Main reconnect loop. Connects, registers, and handles messages.

        Retries forever with exponential backoff on connection failures.
        Backoff resets to base_delay after a successful connection.
        """
        delay = self.base_delay
        while self._running:
            try:
                async with connect(self.config.bot_url) as websocket:
                    self._websocket = websocket
                    delay = self.base_delay  # Reset on successful connect
                    registered = await self._register(websocket)
                    if not registered:
                        # Auth failed -- back off and retry
                        jitter = random.uniform(0, self.jitter_max)
                        wait = min(delay + jitter, self.max_delay + self.jitter_max)
                        await self._sleep(wait)
                        delay = min(delay * 2, self.max_delay)
                        continue
                    await self._message_loop(websocket)
            except (ConnectionClosed, OSError) as exc:
                if not self._running:
                    break
                jitter = random.uniform(0, self.jitter_max)
                wait = min(delay + jitter, self.max_delay + self.jitter_max)
                logger.warning(f"Disconnected ({type(exc).__name__}), reconnecting in {wait:.1f}s...")
                await self._sleep(wait)
                delay = min(delay * 2, self.max_delay)
            except asyncio.CancelledError:
                break
            finally:
                self._websocket = None

    async def _register(self, websocket) -> bool:
        """Send RegisterMessage and wait for Ack or Error.

        Returns True on successful registration, False on rejection.
        Never logs the secret value itself (T-01-11 mitigation).
        """
        msg = RegisterMessage(
            secret=self.config.shared_secret,
            machine_name=self.config.machine_name,
            platform=sys.platform,
        )
        await websocket.send(msg.model_dump_json())

        try:
            raw = await websocket.recv()
        except ConnectionClosed:
            logger.warning("Connection closed during registration")
            return False

        try:
            response = parse_message(raw)
        except Exception:
            logger.error("Invalid response during registration")
            return False

        if isinstance(response, AckMessage):
            logger.info(f"Registered as {self.config.machine_name}")
            return True
        elif isinstance(response, ErrorMessage):
            logger.error(f"Registration rejected: {response.reason}")
            return False
        else:
            logger.error(f"Unexpected response type during registration: {type(response).__name__}")
            return False

    async def _message_loop(self, websocket) -> None:
        """Process incoming messages from the bot server.

        Currently handles HeartbeatPing only. Future phases will add
        command handling.
        """
        async for raw in websocket:
            try:
                msg = parse_message(raw)
            except Exception:
                logger.warning("Received invalid message, ignoring")
                continue

            if isinstance(msg, HeartbeatPing):
                pong = HeartbeatPong(request_id=msg.request_id)
                await websocket.send(pong.model_dump_json())
            else:
                logger.debug(f"Received unhandled message type: {type(msg).__name__}")

    async def stop(self) -> None:
        """Gracefully shut down the agent.

        Sends DisconnectMessage to server before closing the connection.
        """
        self._running = False
        if self._websocket is not None:
            try:
                disconnect = DisconnectMessage()
                await self._websocket.send(disconnect.model_dump_json())
                await self._websocket.close()
            except Exception:
                pass
        logger.info("Agent shutdown complete")
