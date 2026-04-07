<!-- generated-by: gsd-doc-writer -->
# Development

This guide covers everything needed to work on the Discord Terminal Bot codebase: setting up a local dev environment, understanding the project structure, running and writing tests, adding new slash commands, and extending the WebSocket protocol.

---

## Local Setup

### Prerequisites

- **Python >= 3.11** (3.12 recommended). Check with `python --version`.
- `pip` for installing dependencies.
- A Discord bot token (see [CONFIGURATION.md](CONFIGURATION.md) for setup steps).

### Clone and install

```bash
git clone <repo-url>
cd bot_auto_all
pip install -r requirements.txt
```

`requirements.txt` includes both runtime and test dependencies — there is no separate dev requirements file.

### Configure environment files

```bash
# Root .env — shared secret used by both bot and agent
cp .env.example .env

# Bot-specific .env — Discord bot token
cp bot/.env.example bot/.env
```

Edit `.env`:
```dotenv
SHARED_SECRET=change-me-to-a-random-string
```

Edit `bot/.env`:
```dotenv
DISCORD_BOT_TOKEN=your-discord-bot-token-here
SHARED_SECRET=change-me-to-a-random-string
```

Copy and configure `config.json`:
```bash
cp config.example.json config.json
```

Set `discord.allowed_guild_ids` and `discord.allowed_user_ids` in `config.json` before running. The bot silently rejects interactions from unlisted guilds and users.

### Start the bot (development)

```bash
python -m bot
```

The bot starts the WebSocket server first (port 8765 by default), then connects to Discord. Log output goes to stdout and to `logs/bot.log`.

### Start an agent (development)

In a second terminal (or on any machine with network access to the bot):

```bash
python -m agent
```

The agent reads `SHARED_SECRET` and `BOT_URL` from `.env`. Set `BOT_URL=ws://localhost:8765` for local development.

To run both bot and agent on the same machine (useful for integration testing), keep `BOT_URL` at its default `ws://localhost:8765`.

### Enable debug logging

Set `logging.level` to `DEBUG` in `config.json`:

```json
{
    "logging": {
        "level": "DEBUG"
    }
}
```

This increases verbosity for both the bot and agent. Debug logs show individual WebSocket message contents and heartbeat events.

---

## Project Structure

```
bot_auto_all/
├── bot/                  # Bot process — runs on one machine, always on
│   ├── __main__.py       # Entry point: python -m bot
│   ├── discord_bot.py    # TerminalBot class and channel routing API
│   ├── server.py         # AgentManager: WebSocket server, auth, heartbeat
│   ├── config.py         # BotConfig: load from .env + config.json, hot-reload
│   └── cogs/
│       └── general.py    # Slash commands: /status, /ping, /help, /reload
├── agent/                # Agent process — runs on each machine to control
│   ├── __main__.py       # Entry point: python -m agent
│   ├── client.py         # AgentClient: WebSocket client with reconnect backoff
│   └── config.py         # AgentConfig: load from .env + config.json
├── shared/               # Code imported by both bot and agent
│   ├── protocol.py       # Pydantic message models + parse_message()
│   └── constants.py      # Default port, timeouts, intervals
├── tests/                # Pytest test suite
│   ├── conftest.py       # Shared fixtures (BotConfig, ws_server, free_port)
│   ├── test_auth.py      # Access control (AUTH-01, AUTH-04)
│   ├── test_client.py    # AgentClient reconnection logic
│   ├── test_commands.py  # Slash command embed output
│   ├── test_config.py    # Config loading and hot-reload
│   ├── test_handshake.py # Registration protocol
│   ├── test_integration.py # End-to-end bot+agent scenarios
│   ├── test_notifications.py # Connect/disconnect Discord notifications
│   ├── test_protocol.py  # Pydantic message parsing
│   ├── test_routing.py   # Channel-to-agent routing
│   └── test_server.py    # AgentManager heartbeat and eviction
├── config.example.json   # Template for config.json
├── .env.example          # Template for root .env
├── bot/.env.example      # Template for bot/.env
├── pytest.ini            # asyncio_mode=auto, testpaths=tests
└── requirements.txt      # All Python dependencies (pinned)
```

### Separation of bot and agent

`bot/` and `agent/` are independent Python packages. An agent machine only needs `agent/`, `shared/`, and `requirements.txt` — it does not require `discord.py` or `bot/` code. This is intentional: keep the agent footprint minimal.

---

## Key Abstractions

| Class / Function | File | Role |
|---|---|---|
| `TerminalBot` | `bot/discord_bot.py` | `commands.Bot` subclass. Owns channel routing: `get_agent_for_channel()` and `_find_channel_for_agent()`. |
| `AgentManager` | `bot/server.py` | Tracks live WebSocket connections by `machine_name`. Runs authentication and the heartbeat eviction loop. |
| `AgentClient` | `agent/client.py` | Outbound WebSocket client with exponential backoff (1s base, 60s max with jitter). |
| `BotConfig` | `bot/config.py` | All bot runtime config. `reload_config()` and `save_config()` use `asyncio.Lock` to prevent concurrent read/write races. |
| `AgentConfig` | `agent/config.py` | Dataclass holding agent runtime config. |
| `GeneralCog` | `bot/cogs/general.py` | discord.py `Cog` with `/status`, `/help`, `/ping`, `/reload`. `interaction_check()` is the primary auth gate. |
| `parse_message()` | `shared/protocol.py` | Parses raw JSON into typed Pydantic models via a discriminated union on the `type` field. |

---

## Adding a New Slash Command

All bot slash commands live in `bot/cogs/`. The existing cog is `bot/cogs/general.py`.

### Option A: Add to the existing cog

For commands that logically belong with the current set (`/status`, `/ping`, `/help`, `/reload`), add a method to `GeneralCog`:

```python
@app_commands.command(name="mycommand", description="What it does")
async def my_command(self, interaction: discord.Interaction) -> None:
    """Docstring describing the command and any requirement tags."""
    # interaction_check() already ran at this point -- user is authorized
    await interaction.response.send_message("Hello!")
```

The `interaction_check()` method on `GeneralCog` enforces both the guild allowlist and user allowlist before any command handler runs. New commands in this cog inherit that check automatically.

### Option B: Create a new cog

Create `bot/cogs/myfeature.py`:

```python
import discord
from discord import app_commands
from discord.ext import commands


class MyFeatureCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """AUTH gates for this cog. Mirror the pattern in general.py."""
        if interaction.guild_id not in self.bot.bot_config.allowed_guild_ids:
            return False
        if interaction.user.id not in self.bot.bot_config.allowed_user_ids:
            await interaction.response.send_message(
                "You are not authorized to use this bot.", ephemeral=True
            )
            return False
        return True

    @app_commands.command(name="mycommand", description="What it does")
    async def my_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Hello from new cog!")


async def setup(bot: commands.Bot) -> None:
    """Required by discord.py load_extension."""
    await bot.add_cog(MyFeatureCog(bot))
```

Then register the cog in `bot/discord_bot.py` inside `setup_hook()`:

```python
await self.load_extension("bot.cogs.myfeature")
```

**Important:** Always implement `interaction_check()` on new cogs — `default_permissions(administrator=True)` on a cog is UI hiding only, not an authorization gate.

### Routing: from Discord channel to agent

When a slash command needs to send work to a specific agent, use the routing API on `TerminalBot`:

```python
# Inside a command handler: get the machine_name for the current channel
machine_name = self.bot.get_agent_for_channel(interaction.channel_id)
if machine_name is None:
    await interaction.response.send_message("No agent mapped to this channel.", ephemeral=True)
    return

# Then look up the live AgentInfo from AgentManager
agent_info = self.bot.agent_manager.agents.get(machine_name)
if agent_info is None:
    await interaction.response.send_message(f"{machine_name} is offline.", ephemeral=True)
    return

# Send a WebSocket message to the agent
await agent_info.websocket.send(some_message.model_dump_json())
```

---

## Extending the WebSocket Protocol

All protocol messages are Pydantic models in `shared/protocol.py`. The protocol uses a discriminated union on the `type` field.

### Adding a new message type

1. Define the model in `shared/protocol.py`:

```python
class RunCommandMessage(BaseMessage):
    """Bot -> Agent: Execute a shell command."""
    type: Literal["run_command"] = "run_command"
    command: str
    timeout: int = 30
```

2. Add it to the `Message` union:

```python
Message = Annotated[
    Union[
        RegisterMessage,
        AckMessage,
        ErrorMessage,
        HeartbeatPing,
        HeartbeatPong,
        DisconnectMessage,
        RunCommandMessage,   # <- add here
    ],
    Field(discriminator="type"),
]
```

3. Handle the new type in `bot/server.py` (if agent → bot) or in `agent/client.py` `_message_loop()` (if bot → agent).

4. Add a test in `tests/test_protocol.py` to verify the new message round-trips through `parse_message()`.

---

## Running Tests

```bash
pytest
```

The `pytest.ini` sets `asyncio_mode = auto` so all `async def test_*` functions run without extra decorators. The test path is `tests/`.

### Run a specific file

```bash
pytest tests/test_protocol.py
```

### Run a specific test

```bash
pytest tests/test_auth.py::TestUserAllowlist::test_allowed_user_passes
```

### Verbose output

```bash
pytest -v
```

### Run with log output visible

```bash
pytest -s
```

### Test coverage (no threshold configured)

```bash
pytest --cov=bot --cov=agent --cov=shared
```

No minimum coverage thresholds are configured in `pytest.ini` or any coverage config file.

---

## Test Structure

Tests live in `tests/`. The naming convention is `test_<module>.py`. All test files use `pytest-asyncio` (version 1.3.0) with `asyncio_mode = auto`.

### Shared fixtures (`tests/conftest.py`)

| Fixture | Type | Description |
|---|---|---|
| `tmp_env_file` | sync | Writes a `.env` file with test credentials to a temp directory. |
| `tmp_config_file` | sync | Writes a `config.json` with fast test timeouts to a temp directory. |
| `free_port` | sync | Finds an available TCP port using a socket bind. |
| `test_secret` | sync | Returns the string `"test-secret-123"`. |
| `bot_config` | sync | `BotConfig` instance with fast heartbeat/registration timeouts for test speed. |
| `ws_server` | async | Starts a full `AgentManager` + WebSocket server; yields `(manager, port)`; shuts down after test. |
| `ws_uri` | sync | WebSocket URI string pointing to the `ws_server` fixture port. |
| `agent_config` | sync | `AgentConfig` pointing to a test server. |

### Test file overview

| File | What it covers |
|---|---|
| `test_auth.py` | AUTH-01 (user allowlist) and AUTH-04 (guild allowlist) access control logic |
| `test_client.py` | `AgentClient` reconnect backoff, registration success/failure, graceful shutdown |
| `test_commands.py` | Slash command embed output: `/status` matrix (connected, offline, unmapped), `/help` |
| `test_config.py` | `load_bot_config()` and `load_agent_config()` env/file merging; `reload_config()` |
| `test_handshake.py` | WebSocket registration protocol: valid, wrong secret, duplicate name, timeout |
| `test_integration.py` | End-to-end: agent connects → bot notifies → agent disconnects |
| `test_notifications.py` | `_on_agent_connect` and `_on_agent_disconnect` Discord channel messaging |
| `test_protocol.py` | `parse_message()` for all message types; invalid JSON; unknown type |
| `test_routing.py` | `get_agent_for_channel()` and `_find_channel_for_agent()` routing API |
| `test_server.py` | `AgentManager` heartbeat eviction, disconnect callback, concurrent connections |

---

## Code Conventions

### Async everywhere

Both `bot/` and `agent/` are fully async. Use `asyncio.create_subprocess_exec` (not `subprocess.run`) for any subprocess calls to avoid blocking the event loop. Do not call `asyncio.run()` inside discord.py's event loop — use `asyncio.create_task()` or `setup_hook()` patterns instead.

### No `shell=True`

Never use `shell=True` in subprocess calls. Always build explicit argument lists. This is a security constraint, not just style.

### Shared secret never logged

The `SHARED_SECRET` value must never appear in log output. When logging authentication events, log only the result (success/failure) and the `machine_name`, not the secret itself.

### Config mutation pattern

When modifying `channel_mapping` at runtime, always call `await self.bot_config.save_config()` immediately after mutation so the change is persisted. `save_config()` and `reload_config()` both acquire `_config_lock` to prevent concurrent file access.

### Pydantic for all WebSocket messages

Every message crossing the WebSocket boundary must be a Pydantic model defined in `shared/protocol.py`. Do not send raw dicts or manually constructed JSON strings. Serialize with `.model_dump_json()` and parse with `parse_message()`.

### Logging with loguru

Use `from loguru import logger` — do not use stdlib `logging` in new code. Log levels:
- `logger.debug()` — low-level protocol events (message contents, heartbeat ticks)
- `logger.info()` — agent connect/disconnect, config reload, command sync
- `logger.warning()` — recoverable anomalies (heartbeat timeout, unknown message type)
- `logger.error()` — failures that impair a feature (failed Discord send, auth rejection)

---

## Dependency Management

Dependencies are pinned in `requirements.txt`. All packages serve both runtime and test purposes — there is no separate `requirements-dev.txt`. To add a new dependency, add it with an exact version pin:

```
newpackage==1.2.3
```

Key packages and their roles:

| Package | Version | Role |
|---|---|---|
| `discord.py` | 2.7.1 | Discord bot client and slash command framework |
| `websockets` | 16.0 | WebSocket server (bot) and client (agent) |
| `pydantic` | 2.12.5 | Message schema validation via discriminated union |
| `python-dotenv` | 1.2.2 | `.env` file loading |
| `loguru` | 0.7.3 | Structured logging with file rotation |
| `aiofiles` | 23.2.1 | Async read/write for `config.json` |
| `pytest` | 9.0.2 | Test runner |
| `pytest-asyncio` | 1.3.0 | Async test support (`asyncio_mode = auto`) |
