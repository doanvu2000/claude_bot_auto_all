<!-- generated-by: gsd-doc-writer -->
# Configuration

This document covers all configuration options for the Discord Terminal Bot, split across two components: the **bot** (runs the Discord interface and WebSocket server) and the **agent** (runs on each controlled machine).

---

## Environment Variables

Configuration is loaded from `.env` files using `python-dotenv`. The bot loads both the root `.env` and `bot/.env`; the agent loads only the root `.env` at its working directory.

### Bot Environment Variables (`bot/.env` or root `.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DISCORD_BOT_TOKEN` | **Required** | — | Discord bot token from the Discord Developer Portal. Causes startup failure if missing. |
| `SHARED_SECRET` | **Required** | — | Shared secret for agent authentication. Must match the value set on every agent. Causes startup failure if missing. |

### Agent Environment Variables (`.env` at agent working directory)

| Variable | Required | Default | Description |
|---|---|---|---|
| `SHARED_SECRET` | **Required** | — | Shared secret for bot authentication. Must match the value set on the bot. Causes startup failure if missing. |
| `MACHINE_NAME` | Optional | `platform.node()` (hostname) | The name this agent registers under. Shown in Discord notifications and used for channel routing. |
| `BOT_URL` | Optional | `ws://localhost:8765` | WebSocket URL of the bot server the agent connects to. |

#### Minimal `.env` for the bot (`bot/.env`)

```dotenv
DISCORD_BOT_TOKEN=your-bot-token-here
SHARED_SECRET=change-me-to-a-random-string
```

#### Minimal `.env` for an agent (root `.env` on the agent machine)

```dotenv
SHARED_SECRET=change-me-to-a-random-string
MACHINE_NAME=my-workstation
BOT_URL=ws://192.168.1.10:8765
```

> See `.env.example` and `bot/.env.example` in the repository for these templates.

---

## Config File Format (`config.json`)

Beyond environment variables, the bot reads `config.json` at the project root for WebSocket, heartbeat, auth, logging, and Discord routing settings. The agent reads only the `logging` section from this file.

`config.example.json` is the canonical template. Copy it to `config.json` and edit as needed.

```json
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
        "file": "logs/bot.log",
        "rotation": "10 MB",
        "retention": "7 days"
    },
    "discord": {
        "allowed_guild_ids": [123456789012345678],
        "allowed_user_ids": [987654321098765432],
        "channel_mapping": {
            "111222333444555666": "my-pc"
        }
    }
}
```

### Top-Level Keys

| Key | Applies To | Description |
|---|---|---|
| `websocket` | Bot | WebSocket server bind address and port. |
| `heartbeat` | Bot | Intervals for agent health-check pings. |
| `auth` | Bot | Timeout for agent registration handshake. |
| `logging` | Bot and Agent | Log level, file path, rotation, and retention. |
| `discord` | Bot | Guild allowlist, user allowlist, and channel-to-machine mapping. |

---

## Required vs Optional Settings

The following settings cause startup failure if absent:

| Setting | Source | Error on Startup |
|---|---|---|
| `SHARED_SECRET` | `.env` | `ValueError: SHARED_SECRET environment variable is required but not set` |
| `DISCORD_BOT_TOKEN` | `bot/.env` (bot only) | `ValueError: DISCORD_BOT_TOKEN environment variable is required but not set` |

All other settings are optional and have defaults defined in `shared/constants.py`.

---

## Defaults

| Setting | Default Value | Source |
|---|---|---|
| `websocket.host` | `0.0.0.0` | `DEFAULT_WS_HOST` in `shared/constants.py` |
| `websocket.port` | `8765` | `DEFAULT_WS_PORT` in `shared/constants.py` |
| `heartbeat.interval_seconds` | `15` | `DEFAULT_HEARTBEAT_INTERVAL` in `shared/constants.py` |
| `heartbeat.timeout_seconds` | `30` | `DEFAULT_HEARTBEAT_TIMEOUT` in `shared/constants.py` |
| `auth.registration_timeout_seconds` | `10` | `DEFAULT_REGISTRATION_TIMEOUT` in `shared/constants.py` |
| `logging.level` | `INFO` | `DEFAULT_LOG_LEVEL` in `shared/constants.py` |
| `logging.file` (bot) | `logs/bot.log` | Hard-coded default in `bot/config.py` |
| `logging.file` (agent) | `logs/agent.log` | Hard-coded default in `agent/config.py` |
| `logging.rotation` | `10 MB` | `DEFAULT_LOG_ROTATION` in `shared/constants.py` |
| `logging.retention` | `7 days` | `DEFAULT_LOG_RETENTION` in `shared/constants.py` |
| `MACHINE_NAME` (agent) | `platform.node()` (OS hostname) | `agent/config.py` |
| `BOT_URL` (agent) | `ws://localhost:8765` | `agent/config.py` |
| Reconnect base delay | `1.0s` | `DEFAULT_RECONNECT_BASE_DELAY` in `shared/constants.py` |
| Reconnect max delay | `60.0s` | `DEFAULT_RECONNECT_MAX_DELAY` in `shared/constants.py` |
| Reconnect jitter max | `1.0s` | `DEFAULT_RECONNECT_JITTER_MAX` in `shared/constants.py` |

---

## Config File Sections

### `websocket`

Controls the WebSocket server hosted by the bot. Agents connect outbound to this address.

| Key | Type | Default | Description |
|---|---|---|---|
| `host` | string | `"0.0.0.0"` | Bind address for the WebSocket server. Use `0.0.0.0` to accept connections from all interfaces. |
| `port` | integer | `8765` | TCP port the WebSocket server listens on. Must be reachable from all agent machines. |

### `heartbeat`

Controls how the bot checks agent connectivity.

| Key | Type | Default | Description |
|---|---|---|---|
| `interval_seconds` | integer | `15` | How often the bot sends a ping to each connected agent. |
| `timeout_seconds` | integer | `30` | How long the bot waits for a pong before treating the agent as disconnected. |

### `auth`

Controls the agent registration handshake.

| Key | Type | Default | Description |
|---|---|---|---|
| `registration_timeout_seconds` | integer | `10` | How long the bot waits for an agent's registration message after the WebSocket connection is opened. |

### `logging`

Controls log output for both the bot and agent. The agent reads only this section from `config.json`.

| Key | Type | Default | Description |
|---|---|---|---|
| `level` | string | `"INFO"` | Log level. Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `file` | string | `"logs/bot.log"` (bot) / `"logs/agent.log"` (agent) | Path to the log file. Directory must exist or loguru will create it. |
| `rotation` | string | `"10 MB"` | Log file rotation threshold (loguru format). Examples: `"10 MB"`, `"1 day"`. |
| `retention` | string | `"7 days"` | How long old log files are kept before deletion (loguru format). |

### `discord`

Controls Discord access control and channel-to-machine routing. This section is **bot-only**.

| Key | Type | Description |
|---|---|---|
| `allowed_guild_ids` | `list[int]` | Discord server IDs the bot will respond to. Interactions from unlisted guilds are silently rejected (AUTH-04). |
| `allowed_user_ids` | `list[int]` | Discord user IDs permitted to use the bot. <!-- VERIFY: whether allowed_user_ids is enforced at runtime beyond config storage --> |
| `channel_mapping` | `dict[str, str]` | Maps Discord channel IDs (string keys) to machine names. Updated automatically when a new agent connects with no existing mapping. |

#### `channel_mapping` example

```json
"channel_mapping": {
    "1491138095951642775": "my-pc",
    "1491141262340919296": "work-laptop"
}
```

Channel IDs are Discord snowflake integers stored as string keys. Machine names are the `MACHINE_NAME` values reported by agents at registration.

> **Auto-creation:** When an agent connects whose `machine_name` has no entry in `channel_mapping`, the bot automatically creates a new text channel in the first guild listed in `allowed_guild_ids` and writes the new mapping back to `config.json`. A channel with a matching name that already exists will be reused rather than duplicated.

---

## Per-Environment Overrides

There is no separate environment-specific config file mechanism. The recommended approach is:

- **Development:** Use `BOT_URL=ws://localhost:8765` in the agent `.env`. Set `logging.level` to `DEBUG` in `config.json` for verbose output.
- **Production / remote machine:** Set `BOT_URL` in the agent `.env` to the bot's public IP or hostname. <!-- VERIFY: whether TLS (wss://) is supported or planned for production use -->
- All secrets (`SHARED_SECRET`, `DISCORD_BOT_TOKEN`) must always come from `.env` files — never commit them to `config.json` or the repository.

---

## Mutable vs Immutable Settings at Runtime

`config.json` supports hot-reload for certain fields via `BotConfig.reload_config()`. The following fields can be updated in `config.json` and reloaded without restarting the bot:

- `discord.allowed_guild_ids`
- `discord.allowed_user_ids`
- `discord.channel_mapping`

The following require a full bot restart to take effect:

- `DISCORD_BOT_TOKEN` (environment variable, read once at startup)
- `websocket.host` and `websocket.port`
- All `heartbeat` and `auth` settings
