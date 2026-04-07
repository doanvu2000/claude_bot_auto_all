<!-- generated-by: gsd-doc-writer -->
# Getting Started

This guide walks you from a fresh clone to a running bot with at least one agent connected.

---

## Prerequisites

Before you begin, ensure the following are available on the **bot machine**:

- **Python >= 3.11** (3.12 recommended). Python 3.13 is not recommended — some dependencies have ecosystem lag.
- **pip** for installing Python packages.
- A **Discord bot token** from the [Discord Developer Portal](https://discord.com/developers/applications). <!-- VERIFY: link is current -->
- **Git** to clone the repository.

On each **agent machine** (the machines you want to control):

- **Python >= 3.11**
- **pip**
- The `claude` CLI installed and on `PATH` (optional — only required for Claude Code integration).
- Network access to reach the bot machine's IP and port `8765` (outbound TCP — no inbound rules needed on agent machines).

---

## Step 1 — Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application. <!-- VERIFY: link is current -->
2. Under **Bot**, click **Add Bot**, then copy the **Token** — you will need it in Step 3.
3. Under **Bot > Privileged Gateway Intents**, enable **Message Content Intent**.
4. Under **OAuth2 > URL Generator**, select the `bot` and `applications.commands` scopes, then add the `Administrator` permission. Use the generated URL to invite the bot to your Discord server.
5. Note your **Guild (Server) ID** and your own **User ID** — right-click the server icon or your username in Discord (with Developer Mode enabled under Settings > Advanced) to copy them.

---

## Step 2 — Clone and Install (Bot Machine)

```bash
git clone <repo-url>
cd bot_auto_all
pip install -r requirements.txt
```

---

## Step 3 — Configure the Bot

**Copy the example files:**

```bash
cp .env.example .env
cp bot/.env.example bot/.env
cp config.example.json config.json
```

**Edit `.env`** (root — sets the shared secret used by agents):

```dotenv
SHARED_SECRET=change-me-to-a-long-random-string
```

**Edit `bot/.env`** (bot-only credentials):

```dotenv
DISCORD_BOT_TOKEN=your-discord-bot-token-here
SHARED_SECRET=change-me-to-a-long-random-string
```

The `SHARED_SECRET` must be the **same value** in both files and on every agent machine.

**Edit `config.json`** to set your Discord guild and user IDs:

```json
{
    "discord": {
        "allowed_guild_ids": [123456789012345678],
        "allowed_user_ids": [987654321098765432],
        "channel_mapping": {}
    }
}
```

Replace the placeholder IDs with your actual Discord Guild ID and your User ID. The `channel_mapping` can start empty — the bot will auto-create channels when agents connect.

All other `config.json` keys (`websocket`, `heartbeat`, `auth`, `logging`) are optional and have working defaults. See [CONFIGURATION.md](CONFIGURATION.md) for the full reference.

---

## Step 4 — Start the Bot

From the project root on the bot machine:

```bash
python -m bot
```

Expected output (abbreviated):

```
INFO | WebSocket server started on ws://0.0.0.0:8765
INFO | Logged in as YourBot#1234 (id: ...)
INFO | Commands synced to 1 guild(s)
```

Leave this process running. The bot hosts the WebSocket server that agents connect to.

---

## Step 5 — Start an Agent (On Each Machine to Control)

On each machine you want to control, copy the `agent/` and `shared/` directories (and `requirements.txt`) from the repository, then install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the agent's working directory:

```dotenv
SHARED_SECRET=change-me-to-a-long-random-string
MACHINE_NAME=my-pc
BOT_URL=ws://192.168.1.10:8765
```

- `SHARED_SECRET` — must match the value set on the bot.
- `MACHINE_NAME` — a friendly name for this machine (defaults to the OS hostname if omitted).
- `BOT_URL` — the bot machine's IP address and port. Use `ws://localhost:8765` if the agent runs on the same machine as the bot.

Start the agent:

```bash
python -m agent
```

Expected output:

```
INFO | Agent starting: my-pc -> ws://192.168.1.10:8765
INFO | Connected to bot
INFO | Registration acknowledged
```

When the agent connects, the bot posts a notification in the Discord channel mapped to that machine. If no mapping exists yet, the bot automatically creates a new channel and updates `config.json`.

---

## Verify Everything is Working

In your Discord server, use the `/status` slash command. You should see your agent listed as online:

```
Agent Status
🟢 my-pc
  Platform: Windows
  Status: Online (Mapped)
  Last seen: 2s ago
```

Other available slash commands:

| Command | Description |
|---------|-------------|
| `/status` | Show all connected and configured agents |
| `/ping` | Bot health check — shows latency |
| `/help` | List all available commands |
| `/reload` | Hot-reload `config.json` without restarting the bot |

---

## Common Setup Issues

**Bot fails to start: `ValueError: DISCORD_BOT_TOKEN environment variable is required but not set`**

The bot reads `bot/.env` for `DISCORD_BOT_TOKEN`. Confirm the file exists at `bot/.env` (not just the root `.env`) and contains a valid token.

**Bot fails to start: `ValueError: SHARED_SECRET environment variable is required but not set`**

Both `.env` (root) and `bot/.env` must contain `SHARED_SECRET`. The bot loads both files at startup; if either is missing the variable, startup fails.

**Agent connects but Discord shows no notification / no channel created**

Confirm your Guild ID is listed in `config.json` under `allowed_guild_ids`. The bot silently ignores agents if no allowed guild is configured, because it has nowhere to create a channel.

**Agent fails authentication — connection closed immediately**

The `SHARED_SECRET` on the agent does not match the bot's secret. Both sides must have the identical string.

**Slash commands do not appear in Discord**

Commands are synced to guilds listed in `allowed_guild_ids` at startup. Ensure your Guild ID is in that list and restart the bot. Discord can take up to a minute to propagate slash commands.

**Agent cannot reach the bot (`Connection refused` / `Cannot connect`)**

Check that `BOT_URL` in the agent `.env` uses the bot machine's correct IP address and that port `8765` is not blocked by a firewall. The bot machine must allow inbound TCP on port `8765`.

---

## Next Steps

- **[CONFIGURATION.md](CONFIGURATION.md)** — full reference for all environment variables and `config.json` settings, including hot-reload details.
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — how the bot and agent communicate, the security model, and the data flow.
- **[../README.md](../README.md)** — project overview, dependency table, and test instructions.
