<!-- generated-by: gsd-doc-writer -->
# Architecture

## System Overview

Discord Terminal Bot is an event-driven, two-process system that lets a user control remote machines from any Discord client. A long-running **bot process** (hosted on one machine) bridges Discord slash commands and notifications with one or more lightweight **agent processes** (running on each controlled machine). Agents connect outbound to the bot over a persistent WebSocket connection, making the system NAT-friendly with no inbound firewall rules required on agent machines. The bot acts as the sole message router: it maps each Discord channel to exactly one agent's `machine_name`, dispatches commands to the correct agent, and streams results back as Discord messages.

## Component Diagram

```
┌──────────────────────────────────────────────────────┐
│  Bot Machine                                         │
│                                                      │
│  ┌──────────────┐     ┌──────────────────────────┐  │
│  │  TerminalBot │     │      AgentManager        │  │
│  │  (discord.py)│◄───►│  (WebSocket server :8765)│  │
│  │              │     │  heartbeat loop          │  │
│  │  GeneralCog  │     │  agents: dict[name,info] │  │
│  │  /status     │     └──────────────────────────┘  │
│  │  /ping       │              ▲                     │
│  │  /help       │              │ WebSocket (outbound)│
│  │  /reload     │              │                     │
│  └──────┬───────┘   ┌──────────┴──────────┐         │
│         │           │   AgentClient       │ (remote) │
│         │ Discord   │   machine A         │         │
│         │ API       └─────────────────────┘         │
│         │           ┌─────────────────────┐         │
└─────────┼───────────┤   AgentClient       │         │
          │           │   machine B         │         │
    ┌─────▼──────┐    └─────────────────────┘         │
    │  Discord   │                                     │
    │  Servers   │   config.json ──► channel_mapping   │
    └────────────┘   .env ──► SHARED_SECRET, TOKEN     │
```

## Data Flow

A typical interaction follows this path:

1. **Agent startup** — `python -m agent` on a remote machine reads `SHARED_SECRET` and `BOT_URL` from `.env`, then `AgentClient.run()` opens a WebSocket connection outbound to the bot's server (`ws://<host>:8765`).
2. **Registration handshake** — The agent sends a `RegisterMessage` (JSON) containing the shared secret, `machine_name`, and OS platform. `AgentManager._authenticate()` validates the secret, rejects duplicates, and responds with an `AckMessage`.
3. **Connect notification** — `AgentManager` fires the `on_agent_connect` callback, which `TerminalBot._on_agent_connect()` handles. The bot looks up the channel mapped to that `machine_name` in `config.json` and sends a connect notification to that Discord channel. If no mapping exists, the bot auto-creates a Discord channel and updates `config.json`.
4. **Heartbeat monitoring** — Every `heartbeat_interval` seconds (default 15 s) the bot sends a `HeartbeatPing` to each connected agent. Agents reply with `HeartbeatPong`. Agents that do not respond within `heartbeat_timeout` (default 30 s) are evicted and a disconnect notification is posted to their Discord channel.
5. **Slash command** — A Discord user in an allowed guild invokes `/status`, `/ping`, `/help`, or `/reload`. `GeneralCog.interaction_check()` enforces guild allowlist (AUTH-04) and user allowlist (AUTH-01) before any command handler runs. The `global_interaction_check` on the command tree provides a second guild-level gate.
6. **Config hot-reload** — `/reload` calls `BotConfig.reload_config()`, which re-reads `config.json` under an async lock and updates `allowed_guild_ids`, `allowed_user_ids`, and `channel_mapping` in place. No restart required.
7. **Graceful shutdown** — SIGINT/SIGTERM cancels the heartbeat task, closes the WebSocket server, and closes the Discord client cleanly.

## Key Abstractions

| Abstraction | File | Description |
|---|---|---|
| `TerminalBot` | `bot/discord_bot.py` | `commands.Bot` subclass. Owns channel-to-agent routing API: `get_agent_for_channel()` and `_find_channel_for_agent()`. Wires `AgentManager` callbacks to Discord notifications. |
| `AgentManager` | `bot/server.py` | Tracks all live WebSocket connections by `machine_name`. Runs per-connection authentication and the heartbeat eviction loop. |
| `AgentInfo` | `bot/server.py` | Dataclass holding a single agent's `ServerConnection`, `machine_name`, `platform`, and `last_pong` timestamp. |
| `AgentClient` | `agent/client.py` | Outbound WebSocket client with exponential backoff reconnect loop (base 1 s, max 60 s with jitter). |
| `BotConfig` | `bot/config.py` | Holds all bot runtime configuration. Supports async `save_config()` and `reload_config()` with `asyncio.Lock` to prevent concurrent read/write races. |
| `AgentConfig` | `agent/config.py` | Dataclass holding agent runtime configuration loaded from `.env` and `config.json`. |
| `GeneralCog` | `bot/cogs/general.py` | `commands.Cog` with `/status`, `/help`, `/ping`, `/reload`. Contains `interaction_check()` as the primary user and guild auth gate. |
| `Message` (union) | `shared/protocol.py` | Pydantic discriminated union of all protocol message types keyed on the `type` field. `parse_message()` validates raw JSON into typed instances. |

## Protocol Messages

All WebSocket traffic is JSON. Each message carries a `type` discriminator and a UUID `request_id`.

| Message | Direction | Purpose |
|---|---|---|
| `register` | Agent → Bot | Authentication and machine registration (secret, machine_name, platform) |
| `ack` | Bot → Agent | Confirm successful operation |
| `error` | Bot → Agent | Reject with a `reason` string; connection is closed after send |
| `heartbeat_ping` | Bot → Agent | Liveness check |
| `heartbeat_pong` | Agent → Bot | Liveness response; updates `last_pong` timestamp on server |
| `disconnect` | Agent → Bot | Graceful shutdown notification before closing |

## Directory Structure Rationale

```
bot_auto_all/
├── bot/              # Bot process — runs once, always on
│   ├── __main__.py   # Entry point: starts WS server + Discord bot on one event loop
│   ├── discord_bot.py# TerminalBot class and channel routing logic
│   ├── server.py     # AgentManager: WebSocket server, auth, heartbeat
│   ├── config.py     # BotConfig: load, save, hot-reload
│   └── cogs/
│       └── general.py# Slash commands (/status, /ping, /help, /reload)
├── agent/            # Agent process — runs on every controlled machine
│   ├── __main__.py   # Entry point: connect, register, message loop
│   ├── client.py     # AgentClient: connection, registration, heartbeat, backoff
│   └── config.py     # AgentConfig: load from .env and config.json
├── shared/           # Code shared by bot and agent
│   ├── protocol.py   # Pydantic message models and parse_message()
│   └── constants.py  # Default port, timeouts, and intervals
├── tests/            # Pytest test suite
├── config.example.json # Reference config.json template
├── config.json       # Runtime config: channel_mapping, guild/user allowlists
└── requirements.txt  # Python dependencies (pinned versions)
```

`bot/` and `agent/` are intentionally separate Python packages so agents can be deployed with only the `agent/` tree and `shared/` — they do not need `discord.py` or the bot server code.

## Security Model

Access control is layered (defense-in-depth):

1. **Shared secret** (`SHARED_SECRET` env var) — required for every agent to register. Incorrect secret closes the WebSocket immediately.
2. **Guild allowlist** (`allowed_guild_ids` in `config.json`) — enforced at two points: `tree.interaction_check` (global gate on every interaction) and `GeneralCog.interaction_check` (per-cog gate). Commands are also synced only to allowed guilds.
3. **User allowlist** (`allowed_user_ids` in `config.json`) — enforced by `GeneralCog.interaction_check`. Users not in the list receive an ephemeral "not authorized" reply.
4. **`default_permissions(administrator=True)`** on `GeneralCog` — hides commands from non-admin Discord users in the UI only. Not an authoritative security gate.
