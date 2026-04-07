<!-- generated-by: gsd-doc-writer -->
# Testing

## Test Framework and Setup

The project uses **pytest** with the **pytest-asyncio** plugin for async test support.

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | 9.0.2 | Test runner and assertion framework |
| `pytest-asyncio` | 1.3.0 | `async def` test coroutine support |

pytest-asyncio is configured in **auto mode** — all `async def` tests in the `tests/` directory run as coroutines without needing an explicit `@pytest.mark.asyncio` decorator on each one (though some tests carry the marker for clarity).

**Configuration file:** `pytest.ini` at the project root.

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

No additional setup step is required beyond installing dependencies:

```bash
pip install -r requirements.txt
```

## Running Tests

**Run the full test suite:**

```bash
pytest
```

**Run with verbose output (shows each test name and pass/fail):**

```bash
pytest -v
```

**Run a single test file:**

```bash
pytest tests/test_protocol.py
pytest tests/test_integration.py
```

**Run a single test class or function:**

```bash
pytest tests/test_handshake.py::TestHandshake::test_auth_success
pytest tests/test_config.py::TestBotConfig::test_bot_config_loads_shared_secret
```

**Run tests matching a keyword:**

```bash
pytest -k "heartbeat"
pytest -k "auth"
```

**Stop after the first failure:**

```bash
pytest -x
```

Integration tests that start real WebSocket servers are slower than unit tests. To run only fast unit-level tests, skip the integration file:

```bash
pytest --ignore=tests/test_integration.py
```

## Test Structure

All test files live in `tests/`. There is no coverage threshold configured; CI enforcement is not yet set up.

### Test Files

| File | What it covers |
|------|---------------|
| `tests/test_protocol.py` | `shared.protocol` message models and `parse_message()` — creation, serialization, round-trip, validation errors |
| `tests/test_handshake.py` | WebSocket handshake over a real server: auth success, auth failure, malformed JSON, registration timeout, duplicate machine names, re-registration after disconnect |
| `tests/test_server.py` | `bot.server.AgentManager` server lifecycle: connection acceptance, heartbeat ping delivery, pong keep-alive, heartbeat timeout eviction, clean disconnect, multi-agent isolation |
| `tests/test_client.py` | `agent.client.AgentClient` behavior: registration, heartbeat response, reconnection on server close, exponential backoff doubling, backoff cap, backoff reset on success, graceful disconnect on `stop()`, auth rejection logging |
| `tests/test_integration.py` | End-to-end tests using real bot server and real agent client with no transport mocking: full handshake flow, multi-cycle heartbeat keep-alive, agent reconnect after server restart, wrong secret rejection |
| `tests/test_auth.py` | Access control logic: user allowlist, guild allowlist, combined auth matrix (parametrized), check ordering |
| `tests/test_commands.py` | Discord embed construction for `/status` and `/help` slash commands: empty state, connected agents, offline configured agents, footer counts, embed colors |
| `tests/test_notifications.py` | `AgentManager` connect/disconnect callback contract; channel name sanitization logic; Discord `channel.send` failure handling |
| `tests/test_routing.py` | Channel-to-agent mapping: forward lookup, unmapped channels, int vs. string key pitfall, reverse lookup, one-channel-one-agent invariant |
| `tests/test_config.py` | `BotConfig` and `AgentConfig` loading: env var precedence, `config.json` overrides, missing required vars, Discord-specific fields, async `reload_config` and `save_config` |

### Test File Naming

All test files follow the `test_*.py` convention. Test classes use `Test` prefix (`TestBotConfig`, `TestHandshake`). Individual test functions use the `test_` prefix.

## Test Fixtures

Shared fixtures are defined in `tests/conftest.py` and are available to all test files automatically.

| Fixture | Scope | Description |
|---------|-------|-------------|
| `tmp_env_file` | function | Writes a temporary `.env` file with `SHARED_SECRET`, `MACHINE_NAME`, and `BOT_URL` test values. Returns the file path as a string. |
| `tmp_config_file` | function | Writes a temporary `config.json` with WebSocket, heartbeat, auth, and logging sections set to fast test values. Returns the file path as a string. |
| `free_port` | function | Finds and returns a free TCP port on the local machine using `socket.bind(("", 0))`. Used to avoid port conflicts between concurrent tests. |
| `test_secret` | function | Returns the string `"test-secret-123"`. Centralizes the shared secret used across handshake and client tests. |
| `bot_config` | function | Returns a `BotConfig` with `ws_host="127.0.0.1"`, a `free_port`, and fast timeouts (`heartbeat_interval=1`, `heartbeat_timeout=3`, `registration_timeout=2`). |
| `ws_server` | function (async) | Starts a real `AgentManager` WebSocket server, yields `(manager, port)`, then shuts down cleanly. Depends on `bot_config`. |
| `ws_uri` | function | Returns the `ws://127.0.0.1:{port}` URI for the `ws_server` fixture. |
| `agent_config` | function | Returns an `AgentConfig` pointing to a test server with `machine_name="test-agent"`. |

## Writing New Tests

### File placement

Add a new `test_*.py` file under `tests/` or add a test class or function to an existing file that matches the area you are testing.

### Async tests

Because `asyncio_mode = auto` is set, you can write async tests without any decorator:

```python
async def test_my_async_behavior(ws_server, ws_uri, test_secret):
    manager, _ = ws_server
    # test body
```

Adding `@pytest.mark.asyncio` explicitly is also accepted and does no harm.

### Using shared fixtures

Request fixtures by name in the function signature. The most commonly needed fixtures for WebSocket tests are `ws_server`, `ws_uri`, `test_secret`, and `bot_config`.

```python
async def test_example(ws_server, ws_uri, test_secret):
    manager, _ = ws_server
    from websockets.asyncio.client import connect
    from shared.protocol import RegisterMessage, AckMessage, parse_message

    msg = RegisterMessage(secret=test_secret, machine_name="my-test", platform="linux")
    async with connect(ws_uri) as ws:
        await ws.send(msg.model_dump_json())
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        assert isinstance(parse_message(raw), AckMessage)
```

### Parametrized tests

Use `@pytest.mark.parametrize` for matrix-style assertions. See `tests/test_auth.py::TestNegativeAuthPaths::test_auth_matrix` for an example that tests multiple `(user_id, guild_id, allowed_sets, expected)` combinations in one test function.

### Patching environment variables

Use pytest's built-in `monkeypatch` fixture to set or delete environment variables without affecting the real process environment:

```python
def test_my_config(monkeypatch, tmp_path):
    from bot.config import load_bot_config
    monkeypatch.setenv("SHARED_SECRET", "test-value")
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
    config = load_bot_config(config_path=str(tmp_path / "nonexistent.json"))
    assert config.shared_secret == "test-value"
```

When a test must prevent `load_dotenv` from reading a real `.env` file (to test a missing-variable error path), patch `load_dotenv` via `unittest.mock.patch`:

```python
from unittest.mock import patch

def test_missing_secret(monkeypatch, tmp_path):
    from bot.config import load_bot_config
    monkeypatch.delenv("SHARED_SECRET", raising=False)
    with patch("bot.config.load_dotenv"):
        with pytest.raises(ValueError, match="SHARED_SECRET"):
            load_bot_config(config_path=str(tmp_path / "nonexistent.json"))
```

### Agent client tests with custom backoff

`AgentClient` accepts `base_delay`, `max_delay`, and `jitter_max` constructor arguments and an injectable `_sleep` coroutine for testing backoff behavior without real wall-clock delays:

```python
agent = AgentClient(config, base_delay=1.0, max_delay=60.0, jitter_max=0.0)

delays = []
async def mock_sleep(duration):
    delays.append(duration)
    await asyncio.sleep(0.01)

agent._sleep = mock_sleep
```

See `tests/test_client.py::test_backoff_doubles` and `test_backoff_caps_at_max` for complete examples.

## Coverage Requirements

No coverage threshold is configured. The project has no `.nycrc`, `c8` config, or `coverageThreshold` section in any config file.

## CI Integration

No CI pipeline is currently configured. There are no `.github/workflows/` files in the repository. Tests are run manually using `pytest` from the project root.
