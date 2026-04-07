<!-- generated-by: gsd-doc-writer -->
# Discord Terminal Bot

A Discord bot that acts as a remote control interface for multiple computers. Each Discord channel maps to one machine — messages sent in a channel execute shell commands or drive Claude Code sessions on that machine.

## How It Works

The system has two components that run separately:

- **Bot** — runs on one machine, hosts a WebSocket server, and connects to Discord.
- **Agent** — runs on each machine you want to control; connects outbound to the bot's WebSocket server.

Agents connect out through NAT (no port forwarding on agent machines). The bot routes Discord channel interactions to the correct agent based on a `channel_id → machine_name` mapping in `config.json`.

```
Discord ──► Bot (WebSocket server + Discord client)
                  │
        ┌─────────┴──────────┐
      Agent A             Agent B
   (your-pc)           (work-laptop)
```

## Prerequisites

- Python >= 3.11 (3.12 recommended)
- `pip` for dependency installation
- A Discord bot token from the [Discord Developer Portal](https://discord.com/developers/applications) <!-- VERIFY: link is current -->
- The `claude` CLI installed on each agent machine (optional, for Claude Code integration)

## Installation

**On the bot machine:**

```bash
git clone <repo-url>
cd bot_auto_all
pip install -r requirements.txt
```

**On each agent machine** (copy only the `agent/` and `shared/` directories, plus `requirements.txt`):

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Configure the bot

Copy the example environment files and fill in your values:

```bash
cp .env.example .env
cp bot/.env.example bot/.env
```

Edit `.env`:
```
SHARED_SECRET=change-me-to-a-random-string
```

Edit `bot/.env`:
```
DISCORD_BOT_TOKEN=your-discord-bot-token-here
SHARED_SECRET=change-me-to-a-random-string
```

Copy and edit the config file:
```bash
cp config.example.json config.json
```

Add your Discord guild ID and channel-to-machine mappings in `config.json`:
```json
{
    "discord": {
        "allowed_guild_ids": [123456789012345678],
        "allowed_user_ids": [987654321098765432],
        "channel_mapping": {
            "111122223333444455": "my-pc"
        }
    }
}
```

### 2. Start the bot

```bash
python -m bot
```

### 3. Start an agent (on each machine to control)

```bash
SHARED_SECRET=change-me-to-a-random-string BOT_URL=ws://<bot-ip>:8765 python -m agent
```

When the agent connects, the bot posts a notification in the mapped Discord channel. If no channel mapping exists for the agent's machine name, the bot auto-creates a channel in the first allowed guild.

## Configuration

### Environment Variables

| Variable | Required | Component | Description |
|----------|----------|-----------|-------------|
| `SHARED_SECRET` | Yes | Bot + Agent | Shared secret for agent authentication. Must match on both sides. |
| `DISCORD_BOT_TOKEN` | Yes | Bot only | Discord bot token from the developer portal. |
| `MACHINE_NAME` | No | Agent only | Display name for the machine. Defaults to the system hostname. |
| `BOT_URL` | No | Agent only | WebSocket URL of the bot. Defaults to `ws://localhost:8765`. |

### config.json

All values below have defaults; the file is optional but recommended for production use.

| Key | Default | Description |
|-----|---------|-------------|
| `websocket.host` | `0.0.0.0` | Address the WebSocket server binds to. |
| `websocket.port` | `8765` | Port the WebSocket server listens on. |
| `heartbeat.interval_seconds` | `15` | How often the bot pings connected agents. |
| `heartbeat.timeout_seconds` | `30` | Seconds without a pong before an agent is dropped. |
| `auth.registration_timeout_seconds` | `10` | Seconds an agent has to register after connecting. |
| `logging.level` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `logging.file` | `logs/bot.log` | Log file path. |
| `logging.rotation` | `10 MB` | Rotate log file at this size. |
| `logging.retention` | `7 days` | Keep rotated logs for this duration. |
| `discord.allowed_guild_ids` | `[]` | List of Discord server IDs that may use the bot. |
| `discord.allowed_user_ids` | `[]` | List of Discord user IDs authorized to issue commands. |
| `discord.channel_mapping` | `{}` | Map of `"channel_id"` → `"machine_name"`. |

## Running Tests

```bash
pytest
```

Tests live in `tests/` and use `pytest-asyncio`. The suite covers authentication, the WebSocket protocol, agent client reconnection, routing, and Discord notifications.

## Project Structure

```
bot_auto_all/
├── bot/                  # Discord bot + WebSocket server
│   ├── __main__.py       # Entry point: python -m bot
│   ├── discord_bot.py    # TerminalBot — channel-to-agent routing
│   ├── server.py         # AgentManager — WebSocket server, heartbeat
│   ├── config.py         # BotConfig loader (.env + config.json)
│   └── cogs/             # Discord slash command cogs
├── agent/                # Lightweight agent for each controlled machine
│   ├── __main__.py       # Entry point: python -m agent
│   ├── client.py         # AgentClient — WebSocket client with reconnect
│   └── config.py         # AgentConfig loader (.env + config.json)
├── shared/               # Protocol types and constants shared by bot and agent
│   ├── protocol.py       # Pydantic message models + parse_message()
│   └── constants.py      # Default values for ports, timeouts, etc.
├── tests/                # Test suite (pytest + pytest-asyncio)
├── config.example.json   # Example config.json
├── .env.example          # Example root .env (SHARED_SECRET)
├── bot/.env.example      # Example bot .env (DISCORD_BOT_TOKEN)
└── requirements.txt      # Python dependencies
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `discord.py` | 2.7.1 | Discord bot client |
| `websockets` | 16.0 | WebSocket server (bot) and client (agent) |
| `pydantic` | 2.12.5 | Message schema validation |
| `python-dotenv` | 1.2.2 | `.env` file loading |
| `loguru` | 0.7.3 | Structured logging with rotation |
| `aiofiles` | 23.2.1 | Async config file read/write |

## License

No license file detected in this repository. <!-- VERIFY: confirm license status -->
