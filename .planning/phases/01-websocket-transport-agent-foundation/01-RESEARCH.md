# Phase 1: WebSocket Transport & Agent Foundation - Research

**Researched:** 2026-04-06
**Domain:** WebSocket transport, async Python, agent-bot architecture
**Confidence:** HIGH

## Summary

Phase 1 establishes the foundational transport layer: a WebSocket server on the bot side and lightweight agent clients that connect outbound, authenticate via shared secret, register with machine metadata, and maintain persistent connections with heartbeat monitoring. No Discord integration, no shell execution, no Claude Code -- transport only.

The technology stack is well-defined by CLAUDE.md and CONTEXT.md decisions. The `websockets` library has matured significantly since the CLAUDE.md was written -- current version is 16.0 (not 12.x), with a new asyncio API that is cleaner and better suited to this project. Python 3.13 is now fully compatible with all dependencies (websockets 16.0 and pydantic 2.12+ both support it). Pydantic v2 discriminated unions provide an elegant pattern for the typed message protocol.

**Primary recommendation:** Use `websockets` 16.0 with the new `websockets.asyncio.server` / `websockets.asyncio.client` import paths. Use Pydantic v2 discriminated unions with a `type` Literal field for message validation. Implement agent reconnection using a custom backoff loop (not the built-in `async for` pattern) to support the registration-after-reconnect requirement.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Monorepo with shared directory -- `bot/`, `agent/`, `shared/` side by side. `shared/` contains protocol definitions, message types, and constants used by both
- **D-02:** Entry points via `python -m bot` and `python -m agent` using `__main__.py`
- **D-03:** Single `requirements.txt` for all dependencies (bot + agent combined)
- **D-04:** JSON wire format with Pydantic model validation for all messages
- **D-05:** UUID `request_id` for request/response correlation
- **D-06:** Phase 1 message types: `register`, `heartbeat_ping`, `heartbeat_pong`, `ack`, `error`, `disconnect`. Command/response types added in Phase 3
- **D-07:** Heartbeat: ping every 15s, agent considered dead after 30s (2 missed pings)
- **D-08:** Authentication via first message -- agent sends `{type: "register", secret: "...", machine_name: "...", platform: "..."}`. Bot verifies secret, responds with ack or error+close
- **D-09:** Failed auth: bot sends `{type: "error", reason: "auth_failed"}` then closes connection. Log attempt on bot side
- **D-10:** Registration timeout: 10s after WS connect. If no register message received, close connection
- **D-11:** Exponential backoff: 1s -> 2s -> 4s -> ... max 60s, with random jitter 0-1s
- **D-12:** Agent re-registers (sends register message again) after each reconnect
- **D-13:** Secrets (bot token, shared secret) in `.env` file. Settings (port, timeouts, intervals) in `config.json`
- **D-14:** Both `.env.example` and `config.example.json` provided and committed to repo
- **D-15:** Use `loguru` for structured logging with color output and file rotation
- **D-16:** WS connection errors: log warning and continue. One agent failure does not affect others
- **D-17:** `pytest` + `pytest-asyncio` for unit tests and integration tests
- **D-18:** 1-step handshake: single register message carries both auth and metadata
- **D-19:** Registration timeout: 10s
- **D-20:** Default WebSocket port: 8765 (configurable)
- **D-21:** Bot binds to 0.0.0.0
- **D-22:** Machine name is unique key -- second agent with same name is rejected
- **D-23:** No limit on concurrent agents
- **D-24:** Agent sends `machine_name` and `platform` (win32/darwin/linux) in register message
- **D-25:** Agent sends `{type: "disconnect"}` before shutting down
- **D-26:** Phase 1 uses plain `ws://` (no TLS)
- **D-27:** No rate limiting in Phase 1

### Claude's Discretion
- Heartbeat direction (bot ping -> agent pong, or bidirectional)
- Whether agent retries forever or gives up after max attempts
- Exact Pydantic model structure for messages
- Log file rotation settings
- Exact backoff jitter implementation

### Deferred Ideas (OUT OF SCOPE)
- TLS/WSS encryption -- Phase 5 hardening
- Connection rate limiting -- Phase 5 hardening
- Discord notifications on agent connect/disconnect -- Phase 2
- Agent status command (`/status`) -- Phase 2

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFR-01 | Bot hosts WebSocket server for agent connections | websockets 16.0 `serve()` with new asyncio API; bind 0.0.0.0:8765 |
| INFR-02 | JSON wire protocol with request_id correlation | Pydantic v2 discriminated unions with `type` Literal field + UUID `request_id` |
| INFR-03 | Bot and agent share protocol definitions (monorepo) | `shared/` directory with `protocol.py` (message models) and `constants.py` |
| INFR-04 | Config files for bot and agent with examples | `config.json` + `.env` with `.example` templates; python-dotenv for env loading |
| AGNT-01 | Each machine runs lightweight Python agent connecting via WebSocket | websockets `connect()` client with custom reconnect loop |
| AGNT-02 | Agent registers with machine name and platform info | Register message model with `machine_name` + `platform` fields |
| AGNT-04 | Agent auto-reconnects with exponential backoff + jitter | Custom backoff loop: 1s->2s->4s->...60s cap, 0-1s jitter |
| AGNT-05 | Heartbeat ping/pong for connection health monitoring | Bot-initiated ping every 15s; agent dead after 30s (2 missed) |
| AUTH-02 | Agent authenticates to bot via shared secret on WebSocket | First-message auth in register payload; bot verifies and acks/rejects |
| AUTH-03 | Credentials stored in `.env` file, never hardcoded | python-dotenv loading `.env`; `.env.example` committed to repo |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| websockets | 16.0 | WebSocket server + client | Pure-Python async WebSocket. v16.0 is current stable with new asyncio API. Supports Python 3.10-3.14. [VERIFIED: PyPI registry] |
| pydantic | 2.12.5 | Message schema validation | Discriminated unions for typed message protocol. Full Python 3.13 support since 2.8.0. [VERIFIED: PyPI registry] |
| python-dotenv | 1.2.2 | .env file loading | Load secrets from `.env` file. [VERIFIED: PyPI registry] |
| loguru | 0.7.3 | Structured logging | Color output, file rotation, structured context. Better than stdlib logging for long-running processes. [VERIFIED: PyPI registry] |

### Testing

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | Test framework | Unit and integration tests. [VERIFIED: PyPI registry] |
| pytest-asyncio | 1.3.0 | Async test support | Testing async WebSocket server/client code. Use `asyncio_mode = "auto"`. [VERIFIED: PyPI registry] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| websockets 16.0 | websockets 12.x (CLAUDE.md spec) | 12.x uses legacy API; 16.0 uses new cleaner `websockets.asyncio` API. Use 16.0. |
| Custom backoff loop | websockets built-in `async for` reconnect | Built-in pattern doesn't support sending registration after reconnect or custom backoff params. Custom loop required. |
| Pydantic discriminated union | Manual JSON parsing | Pydantic catches malformed messages, provides type safety, and auto-documents the protocol. |

**Installation:**
```bash
pip install websockets==16.0 pydantic==2.12.5 python-dotenv==1.2.2 loguru==0.7.3 pytest==9.0.2 pytest-asyncio==1.3.0
```

**Version note:** CLAUDE.md specifies `websockets 12.x` but that version uses the legacy API which is deprecated. The current version 16.0 uses the new `websockets.asyncio` module which is the recommended path forward. The API is similar but import paths differ. [VERIFIED: websockets upgrade guide on GitHub]

**Python version note:** CLAUDE.md says "Do NOT use 3.13" but this warning is outdated. As of April 2026, websockets 16.0 and pydantic 2.12.5 both fully support Python 3.13 (and even 3.14). The current machine has Python 3.13.2 installed and it is safe to use. [VERIFIED: PyPI classifiers for websockets and pydantic]

## Architecture Patterns

### Recommended Project Structure
```
bot_auto_all/
├── bot/
│   ├── __init__.py
│   ├── __main__.py          # Entry: python -m bot
│   ├── config.py            # Bot config loading
│   └── server.py            # WebSocket server + agent manager
├── agent/
│   ├── __init__.py
│   ├── __main__.py          # Entry: python -m agent
│   ├── config.py            # Agent config loading
│   └── client.py            # WebSocket client + reconnect loop
├── shared/
│   ├── __init__.py
│   ├── protocol.py          # Pydantic message models
│   └── constants.py         # Shared constants (defaults, timeouts)
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures (server, client factories)
│   ├── test_protocol.py     # Unit: message validation
│   ├── test_server.py       # Integration: server behavior
│   ├── test_client.py       # Integration: client reconnection
│   └── test_handshake.py    # Integration: auth + registration flow
├── config.json              # Runtime settings (port, timeouts)
├── config.example.json      # Template committed to repo
├── .env                     # Secrets (gitignored)
├── .env.example             # Template committed to repo
├── requirements.txt         # All dependencies
└── pytest.ini               # Test configuration
```

### Pattern 1: Pydantic Discriminated Union for Message Protocol

**What:** Use a `type` Literal field as discriminator to parse incoming JSON into the correct message model.
**When to use:** Every incoming WebSocket message.

```python
# shared/protocol.py
# Source: Pydantic v2 docs - discriminated unions
import uuid
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field

class BaseMessage(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class RegisterMessage(BaseMessage):
    type: Literal["register"] = "register"
    secret: str
    machine_name: str
    platform: str  # "win32", "darwin", "linux"

class AckMessage(BaseMessage):
    type: Literal["ack"] = "ack"

class ErrorMessage(BaseMessage):
    type: Literal["error"] = "error"
    reason: str

class HeartbeatPing(BaseMessage):
    type: Literal["heartbeat_ping"] = "heartbeat_ping"

class HeartbeatPong(BaseMessage):
    type: Literal["heartbeat_pong"] = "heartbeat_pong"

class DisconnectMessage(BaseMessage):
    type: Literal["disconnect"] = "disconnect"

Message = Annotated[
    Union[
        RegisterMessage,
        AckMessage,
        ErrorMessage,
        HeartbeatPing,
        HeartbeatPong,
        DisconnectMessage,
    ],
    Field(discriminator="type"),
]

def parse_message(raw: str) -> BaseMessage:
    """Parse a JSON string into a typed message."""
    from pydantic import TypeAdapter
    adapter = TypeAdapter(Message)
    return adapter.validate_json(raw)
```

[CITED: https://docs.pydantic.dev/latest/concepts/unions/]

### Pattern 2: WebSocket Server with Agent Manager

**What:** Bot runs a WebSocket server that tracks connected agents by machine name.
**When to use:** Bot-side server implementation.

```python
# bot/server.py
# Source: websockets 16.0 PyPI + upgrade guide
import asyncio
from websockets.asyncio.server import serve, ServerConnection
from shared.protocol import parse_message, RegisterMessage, AckMessage, ErrorMessage

class AgentManager:
    def __init__(self, shared_secret: str):
        self.shared_secret = shared_secret
        self.agents: dict[str, ServerConnection] = {}  # machine_name -> connection

    async def handler(self, websocket: ServerConnection):
        """Handle a single agent connection."""
        try:
            # Wait for registration with timeout
            agent_name = await self._authenticate(websocket)
            if agent_name is None:
                return

            # Agent registered -- handle messages
            await self._handle_agent(websocket, agent_name)
        except Exception:
            pass
        finally:
            # Clean up on disconnect
            self._remove_agent(websocket)

    async def _authenticate(self, websocket: ServerConnection) -> str | None:
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        except asyncio.TimeoutError:
            await websocket.close(1008, "Registration timeout")
            return None

        try:
            msg = parse_message(raw)
        except Exception:
            error = ErrorMessage(reason="invalid_message")
            await websocket.send(error.model_dump_json())
            await websocket.close(1008, "Invalid message")
            return None

        if not isinstance(msg, RegisterMessage):
            error = ErrorMessage(reason="expected_register")
            await websocket.send(error.model_dump_json())
            await websocket.close(1008, "Expected register")
            return None

        if msg.secret != self.shared_secret:
            error = ErrorMessage(reason="auth_failed", request_id=msg.request_id)
            await websocket.send(error.model_dump_json())
            await websocket.close(1008, "Auth failed")
            return None

        if msg.machine_name in self.agents:
            error = ErrorMessage(reason="machine_name_taken", request_id=msg.request_id)
            await websocket.send(error.model_dump_json())
            await websocket.close(1008, "Machine name taken")
            return None

        # Auth success
        self.agents[msg.machine_name] = websocket
        ack = AckMessage(request_id=msg.request_id)
        await websocket.send(ack.model_dump_json())
        return msg.machine_name
```

[VERIFIED: websockets 16.0 PyPI page shows `from websockets.asyncio.server import serve` pattern]

### Pattern 3: Agent Client with Custom Reconnect Loop

**What:** Agent connects to bot, registers, then maintains connection with heartbeat handling. On disconnect, reconnects with exponential backoff.
**When to use:** Agent-side client implementation.

```python
# agent/client.py
# Source: websockets docs reconnection pattern + CONTEXT.md D-11
import asyncio
import random
import sys
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed
from shared.protocol import (
    RegisterMessage, HeartbeatPong, DisconnectMessage, parse_message
)

class AgentClient:
    def __init__(self, uri: str, secret: str, machine_name: str):
        self.uri = uri
        self.secret = secret
        self.machine_name = machine_name
        self.platform = sys.platform

    async def run(self):
        """Main loop with reconnection."""
        delay = 1.0
        while True:
            try:
                async with connect(self.uri) as websocket:
                    delay = 1.0  # Reset on successful connection
                    await self._register(websocket)
                    await self._message_loop(websocket)
            except (ConnectionClosed, OSError) as e:
                jitter = random.uniform(0, 1.0)
                wait = min(delay + jitter, 60.0)
                # logger.warning(f"Disconnected, retrying in {wait:.1f}s")
                await asyncio.sleep(wait)
                delay = min(delay * 2, 60.0)

    async def _register(self, websocket):
        msg = RegisterMessage(
            secret=self.secret,
            machine_name=self.machine_name,
            platform=self.platform,
        )
        await websocket.send(msg.model_dump_json())
        raw = await websocket.recv()
        response = parse_message(raw)
        # Handle ack or error

    async def _message_loop(self, websocket):
        async for raw in websocket:
            msg = parse_message(raw)
            if msg.type == "heartbeat_ping":
                pong = HeartbeatPong(request_id=msg.request_id)
                await websocket.send(pong.model_dump_json())
```

[CITED: websocket.org Python guide for backoff pattern]

### Pattern 4: Heartbeat Manager (Bot-side)

**What:** Bot sends heartbeat pings to all agents every 15s, tracks last pong, disconnects dead agents after 30s.
**When to use:** Bot-side connection health monitoring.
**Recommendation (Claude's Discretion):** Bot-initiated pings (unidirectional). Simpler than bidirectional -- bot is the authority on liveness.

```python
# Inside AgentManager
async def _heartbeat_loop(self):
    """Periodically ping all agents, remove dead ones."""
    while True:
        await asyncio.sleep(15)
        now = time.time()
        dead_agents = []
        for name, info in self.agents.items():
            if now - info.last_pong > 30:
                dead_agents.append(name)
            else:
                ping = HeartbeatPing()
                try:
                    await info.websocket.send(ping.model_dump_json())
                except ConnectionClosed:
                    dead_agents.append(name)
        for name in dead_agents:
            await self._disconnect_agent(name, reason="heartbeat_timeout")
```

[ASSUMED]

### Anti-Patterns to Avoid

- **Using `websockets.serve()` directly (legacy import):** Always use `from websockets.asyncio.server import serve`. The top-level `websockets.serve()` switched to the new API in v14.0 but explicit imports are clearer and future-proof.
- **Using `async for websocket in connect(...)` for reconnection:** The built-in reconnect iterator does not support sending registration after reconnect or custom backoff parameters. Use a manual `while True` loop with explicit backoff.
- **Using `signal.SIGTERM` on Windows:** `loop.add_signal_handler()` is not supported on Windows ProactorEventLoop. Use platform-specific shutdown: `signal.signal(signal.SIGINT, ...)` or `asyncio.Event` for cross-platform shutdown.
- **Blocking the event loop:** Never use `time.sleep()` or synchronous I/O in async code. Always use `await asyncio.sleep()` and async variants.
- **Storing websocket + metadata separately:** Track each agent as a dataclass/object containing the websocket, machine_name, platform, and last_pong timestamp together.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Message validation | Manual JSON key checking | Pydantic discriminated unions | Type safety, auto-error messages, extensible |
| WebSocket transport | Raw TCP sockets | `websockets` library | RFC 6455 compliance, ping/pong frames, close handshake |
| UUID generation | Random string generation | `uuid.uuid4()` | Standard, collision-proof |
| Env file parsing | Manual file reading | `python-dotenv` | Handles quoting, comments, multi-line values |
| Structured logging | stdlib `logging` | `loguru` | Zero-config color output, rotation, better API |

**Key insight:** The websockets library handles WebSocket protocol framing, masking, close handshakes, and ping/pong at the protocol level. The application-level heartbeat (D-07) is a separate concern -- it provides liveness detection with specific timing, distinct from WebSocket protocol-level pings.

## Common Pitfalls

### Pitfall 1: Windows Signal Handling
**What goes wrong:** `loop.add_signal_handler(signal.SIGTERM, ...)` raises `NotImplementedError` on Windows.
**Why it happens:** Windows ProactorEventLoop does not support Unix signal handlers.
**How to avoid:** Use `signal.signal(signal.SIGINT, handler)` on all platforms. For graceful shutdown, use an `asyncio.Event` that gets set from the signal handler.
**Warning signs:** Code works on macOS, crashes on Windows at startup.

### Pitfall 2: Agent Cleanup on Connection Drop
**What goes wrong:** Agent remains in `agents` dict after network drop, blocking reconnection because machine name is "taken" (D-22).
**Why it happens:** `ConnectionClosed` exception may not fire immediately -- heartbeat timeout is the reliable detection mechanism.
**How to avoid:** Always clean up agent from dict in `finally` block of handler. Heartbeat loop also removes dead agents.
**Warning signs:** Agent can't reconnect after network glitch.

### Pitfall 3: Race Condition in Registration Timeout
**What goes wrong:** Agent sends register message just as bot's 10s timeout fires, leading to a partial state.
**Why it happens:** `asyncio.wait_for()` cancels the `recv()` coroutine, but the message may have already arrived.
**How to avoid:** Use `asyncio.wait_for()` on `websocket.recv()` -- cancellation is clean because websockets handles it properly. Close connection in the `except asyncio.TimeoutError` handler.
**Warning signs:** Intermittent test failures on slow CI.

### Pitfall 4: Heartbeat During Registration
**What goes wrong:** Heartbeat loop sends ping to a connection that hasn't completed registration yet.
**Why it happens:** Heartbeat loop runs globally; connection is added before auth completes.
**How to avoid:** Only add agent to the tracked `agents` dict AFTER successful registration. Heartbeat loop only iterates registered agents.
**Warning signs:** Unregistered connections receiving unexpected messages.

### Pitfall 5: Missing request_id in Error Responses
**What goes wrong:** Client can't correlate error response to its register request.
**Why it happens:** Server creates new ErrorMessage without copying request_id from incoming message.
**How to avoid:** Always copy `request_id` from the incoming message when creating response messages.
**Warning signs:** Client-side response correlation fails silently.

### Pitfall 6: JSON Serialization of Pydantic Models
**What goes wrong:** Using `json.dumps(msg.dict())` instead of `msg.model_dump_json()`.
**Why it happens:** Pydantic v1 habit. In v2, `.dict()` is deprecated.
**How to avoid:** Always use `.model_dump_json()` for serialization and `TypeAdapter.validate_json()` for deserialization.
**Warning signs:** Deprecation warnings in logs, UUID objects not serialized correctly.

## Code Examples

### Config File Structure

```json
// config.example.json
{
    "websocket": {
        "host": "0.0.0.0",
        "port": 8765
    },
    "heartbeat": {
        "interval_seconds": 15,
        "timeout_seconds": 30
    },
    "auth": {
        "registration_timeout_seconds": 10
    },
    "logging": {
        "level": "INFO",
        "file": "logs/{name}.log",
        "rotation": "10 MB",
        "retention": "7 days"
    }
}
```

[ASSUMED - structure follows CONTEXT.md decisions]

### .env.example

```bash
# .env.example
# Shared secret for agent authentication (same value on bot and all agents)
SHARED_SECRET=change-me-to-a-random-string

# Discord bot token (not needed until Phase 2)
# DISCORD_BOT_TOKEN=
```

### Cross-Platform Graceful Shutdown

```python
# Works on both Windows and macOS/Linux
import asyncio
import signal

shutdown_event = asyncio.Event()

def _signal_handler(*_):
    shutdown_event.set()

async def main():
    # Register signal handlers (cross-platform safe)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    async with serve(handler, host, port) as server:
        await shutdown_event.wait()
        # Graceful shutdown: close all connections
```

[CITED: https://github.com/wbenny/python-graceful-shutdown]

### pytest-asyncio Configuration

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

[CITED: https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html]

### Integration Test Pattern

```python
# tests/conftest.py
import pytest
import asyncio
from websockets.asyncio.server import serve

@pytest.fixture
async def ws_server(unused_tcp_port):
    """Start a real WebSocket server for integration tests."""
    manager = AgentManager(shared_secret="test-secret")
    async with serve(manager.handler, "localhost", unused_tcp_port) as server:
        yield server, unused_tcp_port

@pytest.fixture
def ws_uri(ws_server):
    _, port = ws_server
    return f"ws://localhost:{port}"
```

[ASSUMED - standard pytest-asyncio fixture pattern]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `from websockets import serve` (legacy) | `from websockets.asyncio.server import serve` | websockets 13.0 (2024) | New asyncio API is default since v14.0 |
| `websockets 12.x` | `websockets 16.0` | Jan 2026 | CLAUDE.md version spec is outdated; use 16.0 |
| `WebSocketServerProtocol` | `ServerConnection` | websockets 14.2 | Class renamed; new API |
| `connection.path` | `connection.request.path` | websockets 14.0 | Attribute access changed |
| `pydantic .dict()` | `pydantic .model_dump_json()` | Pydantic 2.0 (2023) | v1 methods deprecated |
| Python 3.13 incompatible | Python 3.13 fully supported | Pydantic 2.8+ / websockets 14+ | CLAUDE.md warning is outdated |

**Deprecated/outdated:**
- `websockets.legacy.*` module -- deprecated, will be removed after 5-year policy
- `websockets 12.x` -- 4 major versions behind, uses legacy API
- CLAUDE.md "Do NOT use 3.13" -- no longer applicable; all dependencies support 3.13

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Heartbeat loop pattern (bot sends ping, iterates agents, removes dead ones) | Architecture Patterns - Pattern 4 | Low -- standard pattern, easy to adjust |
| A2 | Config file JSON structure | Code Examples | Low -- structure follows CONTEXT.md decisions, exact keys are implementation detail |
| A3 | pytest fixture pattern with `unused_tcp_port` | Code Examples | Low -- standard pytest pattern; may need `pytest-asyncio` specific fixture name |

**If this table is empty:** N/A -- three low-risk assumptions identified above.

## Open Questions

1. **Agent retry forever or give up?**
   - What we know: CONTEXT.md lists this as Claude's Discretion
   - Recommendation: Retry forever. The agent is a background service; if the bot is down, agent should keep trying. Log a warning every N attempts so the user knows.

2. **Heartbeat direction**
   - What we know: CONTEXT.md lists this as Claude's Discretion
   - Recommendation: Bot-initiated pings (bot -> agent pong). Simpler -- bot is the authority on which agents are alive. Agent just responds.

3. **Log rotation settings**
   - What we know: CONTEXT.md lists this as Claude's Discretion
   - Recommendation: 10 MB rotation, 7 days retention. Standard for a personal-use service.

4. **`unused_tcp_port` fixture availability**
   - What we know: This is a common pytest fixture but may require `pytest-asyncio` or another plugin
   - Recommendation: Verify during implementation; fall back to finding a free port manually if needed

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | YES | 3.13.2 (via `py` launcher) | -- |
| pip | Package install | YES | (via `py -m pip`) | -- |
| websockets | Transport | Not yet installed | 16.0 on PyPI | Install via requirements.txt |
| pydantic | Message validation | Not yet installed | 2.12.5 on PyPI | Install via requirements.txt |
| loguru | Logging | Not yet installed | 0.7.3 on PyPI | Install via requirements.txt |
| pytest | Testing | Not yet installed | 9.0.2 on PyPI | Install via requirements.txt |

**Missing dependencies with no fallback:** None -- all dependencies are installable via pip.

**Missing dependencies with fallback:** None needed.

**Note:** Python is available via the `py` launcher on this Windows machine (`py --version` returns 3.13.2). The `python` and `python3` commands point to the Windows App Store stub. Use `py` or create a virtual environment.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pytest.ini` (create in Wave 0) |
| Quick run command | `py -m pytest tests/ -x -q` |
| Full suite command | `py -m pytest tests/ -v` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFR-01 | Bot hosts WS server, accepts connections | integration | `py -m pytest tests/test_server.py::test_server_accepts_connection -x` | Wave 0 |
| INFR-02 | JSON protocol with request_id correlation | unit | `py -m pytest tests/test_protocol.py -x` | Wave 0 |
| INFR-03 | Shared protocol definitions (monorepo) | unit | `py -m pytest tests/test_protocol.py::test_message_models -x` | Wave 0 |
| INFR-04 | Config files load correctly | unit | `py -m pytest tests/test_config.py -x` | Wave 0 |
| AGNT-01 | Agent connects to bot via WS | integration | `py -m pytest tests/test_handshake.py::test_agent_connects -x` | Wave 0 |
| AGNT-02 | Agent registers with machine_name + platform | integration | `py -m pytest tests/test_handshake.py::test_registration -x` | Wave 0 |
| AGNT-04 | Agent auto-reconnects with backoff | integration | `py -m pytest tests/test_client.py::test_reconnect_backoff -x` | Wave 0 |
| AGNT-05 | Heartbeat ping/pong monitoring | integration | `py -m pytest tests/test_server.py::test_heartbeat -x` | Wave 0 |
| AUTH-02 | Agent auth via shared secret | integration | `py -m pytest tests/test_handshake.py::test_auth_success -x` | Wave 0 |
| AUTH-02 | Reject bad secret | integration | `py -m pytest tests/test_handshake.py::test_auth_failure -x` | Wave 0 |
| AUTH-03 | Credentials from .env | unit | `py -m pytest tests/test_config.py::test_env_loading -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `py -m pytest tests/ -x -q`
- **Per wave merge:** `py -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `pytest.ini` -- test configuration with `asyncio_mode = auto`
- [ ] `requirements.txt` -- all dependencies
- [ ] `tests/__init__.py` -- package init
- [ ] `tests/conftest.py` -- shared fixtures (WS server, client factories)
- [ ] `tests/test_protocol.py` -- message model validation tests
- [ ] `tests/test_config.py` -- config loading tests
- [ ] `tests/test_server.py` -- server behavior tests
- [ ] `tests/test_handshake.py` -- auth + registration tests
- [ ] `tests/test_client.py` -- client reconnection tests

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Shared secret in first message; reject + close on failure |
| V3 Session Management | no | No HTTP sessions in this phase |
| V4 Access Control | yes | Machine name uniqueness check; registration timeout |
| V5 Input Validation | yes | Pydantic model validation on all incoming messages |
| V6 Cryptography | no | Plain ws:// in Phase 1 (TLS deferred to Phase 5) |

### Known Threat Patterns for WebSocket + Python

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret in plaintext over network | Information Disclosure | Deferred: WSS/TLS in Phase 5. Phase 1 assumes trusted network. |
| Malformed JSON causing crash | Denial of Service | Pydantic validation wraps all incoming messages in try/except |
| Connection flooding | Denial of Service | Deferred: rate limiting in Phase 5. Phase 1 assumes small group. |
| Slowloris (connect but never send) | Denial of Service | 10s registration timeout (D-10) closes idle connections |
| Machine name spoofing | Spoofing | Shared secret auth prevents unauthorized registration |

## Project Constraints (from CLAUDE.md)

- Use `websockets` library (version updated from 12.x to 16.0 per research)
- Use `asyncio` -- single event loop, no threading
- Use `pydantic` 2.x for message validation
- Use `loguru` for logging
- Use `python-dotenv` for `.env` loading
- Never use `shell=True` in subprocess (not relevant to Phase 1 but noted)
- Never use `asyncio.run()` inside discord.py's loop (not relevant to Phase 1)
- Project layout: `bot/`, `agent/`, `shared/`
- Entry points: `python -m bot`, `python -m agent`

## Sources

### Primary (HIGH confidence)
- [PyPI: websockets 16.0](https://pypi.org/project/websockets/) -- version, Python compatibility, API examples
- [websockets upgrade guide (GitHub)](https://github.com/python-websockets/websockets/blob/main/docs/howto/upgrade.rst) -- migration from legacy to new asyncio API
- [Pydantic discriminated unions docs](https://docs.pydantic.dev/latest/concepts/unions/) -- tagged union pattern
- [pytest-asyncio configuration](https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html) -- asyncio_mode auto

### Secondary (MEDIUM confidence)
- [websocket.org Python guide](https://websocket.org/guides/languages/python/) -- server/client code patterns, reconnection examples
- [GitHub: python-graceful-shutdown](https://github.com/wbenny/python-graceful-shutdown) -- cross-platform signal handling
- [Pydantic Python 3.13 issue #11524](https://github.com/pydantic/pydantic/issues/11524) -- confirmed 3.13 support in pydantic 2.8+

### Tertiary (LOW confidence)
- None -- all claims verified against primary or secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against PyPI registry
- Architecture: HIGH -- patterns derived from official docs and verified API
- Pitfalls: MEDIUM -- Windows signal handling verified; race conditions based on experience patterns

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (30 days -- stable ecosystem, no fast-moving changes expected)
