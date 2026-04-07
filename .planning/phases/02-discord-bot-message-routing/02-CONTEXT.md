# Phase 2: Discord Bot & Message Routing - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Bot joins Discord, routes channel messages to the correct machine agent via slash commands, enforces access control (user ID + guild ID allowlist), and displays agent status. This phase delivers Discord integration and routing only — no shell execution (Phase 3), no Claude Code (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Bot-WS Integration
- **D-01:** Discord bot and WebSocket server run in the same process, sharing a single asyncio event loop. AgentManager is accessed directly by the Discord bot — no IPC needed
- **D-02:** Entry point remains `python -m bot`. Startup sequence: WS server starts first (agents can connect immediately), then Discord bot connects
- **D-03:** Bot graceful shutdown tears down both Discord connection and WS server

### Message Interpretation
- **D-04:** Slash commands only — no prefix commands, no raw message interpretation. Every interaction goes through Discord application commands
- **D-05:** Slash commands are channel-based: command in a mapped channel auto-targets that channel's agent. Unmapped channels reject with ephemeral error
- **D-06:** When target agent is offline, bot replies with ephemeral error: "Agent [name] is offline"
- **D-07:** Output formatting/truncation deferred to Phase 3. Phase 2 only handles routing and raw response relay

### Slash Commands
- **D-08:** Phase 2 slash commands: `/status` (show all agents), `/help` (list commands), `/ping` (bot health check), `/reload` (hot-reload config.json)
- **D-09:** `/status` displays as Discord embed with color, fields per agent (name, platform, status, uptime). `/help` also as embed
- **D-10:** `/status` and `/help` responses are visible (entire channel can see), not ephemeral
- **D-11:** Slash commands synced as guild commands (instant sync) to guilds in `allowed_guild_ids` — not global commands

### Channel Mapping & Config
- **D-12:** Channel-to-agent mapping stored in `config.json` under `channel_mapping` key: `{"channel_id": "machine_name"}`. Same file also holds `allowed_user_ids` and `allowed_guild_ids`
- **D-13:** `/reload` slash command hot-reloads config.json without bot restart. Allows adding new machines/channels at runtime
- **D-14:** When an agent connects with no channel mapped, bot auto-creates a Discord channel named after `machine_name` in the guild, updates config.json with the new mapping, and sends connection notification

### Access Control
- **D-15:** Slash commands are hidden from unauthorized users via Discord permissions. Unauthorized users cannot see or invoke bot commands
- **D-16:** Guild ID allowlist enforced — bot ignores guilds not in `allowed_guild_ids`

### Discord Token & Environment
- **D-17:** Discord bot token stored in separate `bot/.env` file. Root `.env` keeps shared secret only. Separates bot-specific secrets from shared infrastructure secrets
- **D-18:** `bot/.env.example` provided with `DISCORD_BOT_TOKEN=` placeholder

### Discord Intents
- **D-19:** Minimal intents only — `discord.Intents.default()`. No `message_content` privileged intent needed since all interaction is through slash commands. No `members` intent needed

### Agent Status Notifications
- **D-20:** Agent connect/disconnect notifications sent to the agent's mapped Discord channel. Format: "🟢 **name** connected (platform)" / "🔴 **name** disconnected"
- **D-21:** Reconnection after WS drop also notified: "🟢 **name** reconnected"
- **D-22:** WS connection drops detected via existing heartbeat mechanism (30s timeout from Phase 1). Notification sent to mapped channel on detection

### Claude's Discretion
- Exact embed color scheme and field layout for /status and /help
- Discord channel category for auto-created channels
- Error message wording details
- /reload permission (any allowed user or admin-only)
- How /ping response is formatted

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 Foundation
- `bot/server.py` — AgentManager class, agent tracking dict, heartbeat loop. Phase 2 Discord bot integrates directly with this
- `bot/config.py` — BotConfig class. Must be extended with Discord token, channel mapping, allowlists
- `shared/protocol.py` — Pydantic message models. Phase 2 may add notification-related types
- `shared/constants.py` — Default values for ports, timeouts. Add Discord-related defaults here
- `bot/__main__.py` — Entry point. Must be modified to start both WS server and Discord bot

### Project-Level
- `CLAUDE.md` — Tech stack decisions (discord.py 2.3.x, asyncio patterns, what NOT to use)
- `.planning/REQUIREMENTS.md` — Requirements ROUT-01 through ROUT-05, AUTH-01, AUTH-04, AGNT-03, AGNT-06

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AgentManager` (bot/server.py): Already tracks agents by machine_name with AgentInfo dataclass (websocket, machine_name, platform, last_pong). Discord bot can query this directly
- `BotConfig` (bot/config.py): Config loading pattern with .env + config.json merge. Extend for Discord settings
- `parse_message()` (shared/protocol.py): Pydantic-based message parsing. Pattern for any new message types
- `loguru` logging: Already configured with rotation and structured output

### Established Patterns
- Async-first: Everything uses asyncio, no threading
- Pydantic validation for all wire messages
- Config: environment variables for secrets, config.json for settings
- Signal handling (SIGINT/SIGTERM) for graceful shutdown in bot/__main__.py

### Integration Points
- `AgentManager.agents` dict: Discord bot reads this to check agent availability and route commands
- `AgentManager.handler()`: Per-connection handler — may need callbacks for agent connect/disconnect events to trigger Discord notifications
- `bot/__main__.py`: Must orchestrate both WS server and Discord bot startup on same event loop
- Phase 3 will add `/run` and `/kill` commands that use the routing infrastructure built here

</code_context>

<specifics>
## Specific Ideas

- Auto-channel creation: when agent connects without a mapped channel, bot creates `#machine-name` channel automatically and updates config.json. Zero manual setup for new machines
- CLAUDE.md warns against `asyncio.run()` inside discord.py's loop — use `bot.loop.create_task()` or `setup_hook()` patterns
- discord.py 2.x app_commands module for slash commands — use `@app_commands.command()` decorator pattern

</specifics>

<deferred>
## Deferred Ideas

- TLS/WSS encryption — Phase 5 hardening
- Rate limiting per user — Phase 5 (AUTH-05)
- Shell command execution (/run, /kill) — Phase 3
- Claude Code integration (/claude, /shell, /new-session) — Phase 4
- Output truncation + file attachment for long output — Phase 3
- Role-based permissions (Discord roles instead of user ID allowlist) — v2

</deferred>

---

*Phase: 02-discord-bot-message-routing*
*Context gathered: 2026-04-07*
