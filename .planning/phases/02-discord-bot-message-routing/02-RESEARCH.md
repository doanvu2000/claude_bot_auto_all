# Phase 02: Discord Bot & Message Routing - Research

**Researched:** 2026-04-07
**Domain:** Discord bot integration, slash commands, message routing, access control
**Confidence:** HIGH

## Summary

Phase 2 builds the Discord-facing layer on top of Phase 1's WebSocket infrastructure. The bot joins Discord, registers slash commands per guild, routes interactions to the correct agent via channel-to-machine mapping, enforces user/guild allowlists, and sends agent connect/disconnect notifications. No shell execution or Claude Code integration -- just routing and access control.

The discord.py 2.7.x library provides all needed primitives: `app_commands` for slash commands, `CommandTree.sync(guild=...)` for instant guild-scoped command registration, `Embed` for rich status displays, `guild.create_text_channel()` for auto-channel creation, and `interaction.response.send_message(ephemeral=True)` for private error messages.

**Primary recommendation:** Subclass `commands.Bot`, use `setup_hook()` to sync guild commands, implement an `app_commands.check` decorator for user ID allowlist enforcement, and add callback hooks to `AgentManager` for connect/disconnect Discord notifications.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Discord bot and WebSocket server run in the same process, sharing a single asyncio event loop. AgentManager is accessed directly by the Discord bot -- no IPC needed
- **D-02:** Entry point remains `python -m bot`. Startup sequence: WS server starts first (agents can connect immediately), then Discord bot connects
- **D-03:** Bot graceful shutdown tears down both Discord connection and WS server
- **D-04:** Slash commands only -- no prefix commands, no raw message interpretation
- **D-05:** Slash commands are channel-based: command in a mapped channel auto-targets that channel's agent. Unmapped channels reject with ephemeral error
- **D-06:** When target agent is offline, bot replies with ephemeral error: "Agent [name] is offline"
- **D-07:** Output formatting/truncation deferred to Phase 3. Phase 2 only handles routing and raw response relay
- **D-08:** Phase 2 slash commands: `/status` (show all agents), `/help` (list commands), `/ping` (bot health check), `/reload` (hot-reload config.json)
- **D-09:** `/status` displays as Discord embed with color, fields per agent (name, platform, status, uptime). `/help` also as embed
- **D-10:** `/status` and `/help` responses are visible (entire channel can see), not ephemeral
- **D-11:** Slash commands synced as guild commands (instant sync) to guilds in `allowed_guild_ids` -- not global commands
- **D-12:** Channel-to-agent mapping stored in `config.json` under `channel_mapping` key: `{"channel_id": "machine_name"}`. Same file also holds `allowed_user_ids` and `allowed_guild_ids`
- **D-13:** `/reload` slash command hot-reloads config.json without bot restart
- **D-14:** When an agent connects with no channel mapped, bot auto-creates a Discord channel named after `machine_name` in the guild, updates config.json with the new mapping, and sends connection notification
- **D-15:** Slash commands are hidden from unauthorized users via Discord permissions. Unauthorized users cannot see or invoke bot commands
- **D-16:** Guild ID allowlist enforced -- bot ignores guilds not in `allowed_guild_ids`
- **D-17:** Discord bot token stored in separate `bot/.env` file. Root `.env` keeps shared secret only
- **D-18:** `bot/.env.example` provided with `DISCORD_BOT_TOKEN=` placeholder
- **D-19:** Minimal intents only -- `discord.Intents.default()`. No `message_content` privileged intent needed
- **D-20:** Agent connect/disconnect notifications sent to mapped Discord channel
- **D-21:** Reconnection after WS drop also notified
- **D-22:** WS connection drops detected via existing heartbeat mechanism (30s timeout from Phase 1)

### Claude's Discretion
- Exact embed color scheme and field layout for /status and /help
- Discord channel category for auto-created channels
- Error message wording details
- /reload permission (any allowed user or admin-only)
- How /ping response is formatted

### Deferred Ideas (OUT OF SCOPE)
- TLS/WSS encryption -- Phase 5 hardening
- Rate limiting per user -- Phase 5 (AUTH-05)
- Shell command execution (/run, /kill) -- Phase 3
- Claude Code integration (/claude, /shell, /new-session) -- Phase 4
- Output truncation + file attachment for long output -- Phase 3
- Role-based permissions (Discord roles instead of user ID allowlist) -- v2
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ROUT-01 | Each Discord channel maps to exactly one machine (channel-per-machine routing) | `config.json` channel_mapping dict, AgentManager lookup by machine_name |
| ROUT-02 | Channel-to-agent mapping configured via static config file (channel IDs) | BotConfig extension with channel_mapping, allowed_user_ids, allowed_guild_ids |
| ROUT-03 | Messages in unmapped channels are ignored silently | `app_commands.check` returns False for unmapped channels, or ephemeral error per D-05 |
| ROUT-04 | `/help` command lists all available bot commands | Embed-based slash command with command descriptions |
| ROUT-05 | Bot runs on user's own machine -- no VPS required | Single process entry point `python -m bot`, no external services |
| AUTH-01 | Discord user ID allowlist enforced on every command execution | `app_commands.check` decorator verifying interaction.user.id against config |
| AUTH-04 | Guild (server) ID allowlist -- bot rejects unauthorized Discord servers | Guild check in `setup_hook` (only sync to allowed guilds) + interaction check |
| AGNT-03 | Machine online/offline status displayed in Discord when agent connects/disconnects | Callback hooks on AgentManager for connect/disconnect events |
| AGNT-06 | `/status` command shows all connected agents and their state | Read AgentManager.agents dict, build Discord Embed |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.7.1 | Discord bot framework | Latest stable release (March 2026). Full app_commands support, async-native, guild command sync. [VERIFIED: PyPI via WebSearch] |
| websockets | 16.0 | Agent WS transport | Already installed from Phase 1. [VERIFIED: requirements.txt] |
| pydantic | 2.12.5 | Message validation | Already installed from Phase 1. [VERIFIED: requirements.txt] |
| python-dotenv | 1.2.2 | .env file loading | Already installed from Phase 1. [VERIFIED: requirements.txt] |
| loguru | 0.7.3 | Structured logging | Already installed from Phase 1. [VERIFIED: requirements.txt] |
| aiofiles | 23.2.1 | Async file I/O | Already installed. Needed for async config.json rewrite during auto-channel creation. [VERIFIED: requirements.txt] |

### New Dependency
| Library | Version | Purpose |
|---------|---------|---------|
| discord.py | 2.7.1 | Must be added to requirements.txt |

**Installation:**
```bash
pip install discord.py==2.7.1
```

**Note on Python version:** The development machine has Python 3.13.2 installed via `py` launcher. CLAUDE.md recommends 3.11 minimum, prefer 3.12, and warns about 3.13. discord.py 2.7.1 should be compatible with 3.13 but this should be verified during implementation. [ASSUMED]

## Architecture Patterns

### Recommended Project Structure
```
bot/
  __init__.py          # existing
  __main__.py          # MODIFY: orchestrate WS server + Discord bot
  config.py            # MODIFY: add Discord token, channel_mapping, allowlists
  server.py            # MODIFY: add callback hooks for agent connect/disconnect
  discord_bot.py       # NEW: Discord bot class, setup_hook, event handlers
  cogs/
    __init__.py        # NEW
    general.py         # NEW: /status, /help, /ping, /reload commands
bot/.env               # NEW: DISCORD_BOT_TOKEN
bot/.env.example       # NEW: placeholder
shared/
  constants.py         # MODIFY: add Discord-related defaults
  protocol.py          # existing (may not need changes)
config.json            # MODIFY: add channel_mapping, allowed_user_ids, allowed_guild_ids
```

### Pattern 1: Bot Subclass with setup_hook
**What:** Subclass `commands.Bot` to hold references to `AgentManager` and `BotConfig`. Use `setup_hook()` for guild command sync.
**When to use:** Always -- this is the standard discord.py 2.x pattern.
**Example:**
```python
# Source: discord.py official examples (basic.py, advanced_startup.py)
import discord
from discord.ext import commands

class TerminalBot(commands.Bot):
    def __init__(self, agent_manager, config):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)  # prefix unused but required
        self.agent_manager = agent_manager
        self.bot_config = config

    async def setup_hook(self):
        # Sync slash commands to each allowed guild (instant, no 1-hour wait)
        for guild_id in self.bot_config.allowed_guild_ids:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
```
[VERIFIED: discord.py GitHub examples]

### Pattern 2: Cog for Slash Commands
**What:** Group related commands in a `Cog` class using `@app_commands.command()`.
**When to use:** For organizing the 4 Phase 2 commands (`/status`, `/help`, `/ping`, `/reload`).
**Example:**
```python
# Source: discord.py docs pattern
from discord import app_commands
from discord.ext import commands

class GeneralCog(commands.Cog):
    def __init__(self, bot: TerminalBot):
        self.bot = bot

    @app_commands.command(name="status", description="Show all connected agents")
    async def status(self, interaction: discord.Interaction):
        agents = self.bot.agent_manager.agents
        embed = discord.Embed(title="Agent Status", color=0x2ECC71)
        for name, info in agents.items():
            uptime = int(time.time() - info.last_pong)
            embed.add_field(
                name=name,
                value=f"Platform: {info.platform}\nStatus: Online\nLast seen: {uptime}s ago",
                inline=False,
            )
        if not agents:
            embed.description = "No agents connected"
            embed.color = 0x95A5A6
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ping", description="Bot health check")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! Latency: {latency}ms")
```
[VERIFIED: discord.py app_commands pattern from official docs]

### Pattern 3: Access Control via app_commands.check
**What:** Custom check decorator that verifies user ID is in allowlist before command execution.
**When to use:** Every slash command.
**Example:**
```python
def is_allowed_user():
    async def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client
        if interaction.user.id not in bot.bot_config.allowed_user_ids:
            await interaction.response.send_message(
                "You are not authorized.", ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

# Apply to all commands in a cog via cog_check:
class GeneralCog(commands.Cog):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id in interaction.client.bot_config.allowed_user_ids
```
[VERIFIED: discord.py app_commands.check documentation]

### Pattern 4: AgentManager Callbacks for Discord Notifications
**What:** Add callback hooks to AgentManager so the Discord bot can react to agent events.
**When to use:** Agent connect/disconnect notifications (D-20, D-21, D-22).
**Example:**
```python
# In AgentManager.__init__:
self.on_agent_connect: Callable[[str, str], Awaitable[None]] | None = None
self.on_agent_disconnect: Callable[[str], Awaitable[None]] | None = None

# In AgentManager._authenticate after successful registration:
if self.on_agent_connect:
    await self.on_agent_connect(msg.machine_name, msg.platform)

# In AgentManager._remove_agent:
if self.on_agent_disconnect:
    await self.on_agent_disconnect(machine_name)
```
[ASSUMED -- design pattern, not library-specific]

### Pattern 5: Same-Process Event Loop (D-01, D-02)
**What:** Run WS server and Discord bot on the same asyncio event loop. WS starts first, then Discord.
**When to use:** `__main__.py` entry point.
**Example:**
```python
# Source: CLAUDE.md -- "discord.py manages its own event loop"
async def run_all(config):
    manager = AgentManager(config)
    
    # Start WS server first (agents can connect immediately)
    ws_server = await serve(manager.handler, config.ws_host, config.ws_port)
    heartbeat_task = asyncio.create_task(manager._heartbeat_loop())
    
    # Create and start Discord bot (shares event loop)
    bot = TerminalBot(manager, config)
    
    # Register callbacks for Discord notifications
    bot.setup_agent_callbacks(manager)
    
    try:
        await bot.start(config.discord_token)
    finally:
        heartbeat_task.cancel()
        ws_server.close()
        await ws_server.wait_closed()
        await bot.close()
```
[VERIFIED: CLAUDE.md warns against asyncio.run() inside discord.py loop; bot.start() is the correct non-blocking approach]

### Pattern 6: Auto-Channel Creation (D-14)
**What:** When an agent connects with no mapped channel, create a text channel in the guild.
**Example:**
```python
async def auto_create_channel(self, machine_name: str, guild_id: int):
    guild = self.get_guild(guild_id)
    if guild is None:
        return
    # Create channel with sanitized name
    channel_name = machine_name.lower().replace(" ", "-").replace("_", "-")
    channel = await guild.create_text_channel(channel_name)
    # Update config.json
    self.bot_config.channel_mapping[str(channel.id)] = machine_name
    await self.bot_config.save_config()  # async write via aiofiles
```
[VERIFIED: discord.py guild.create_text_channel() API from GitHub source]

### Anti-Patterns to Avoid
- **`asyncio.run()` inside discord.py's loop:** discord.py manages its own event loop. Use `bot.start()` (coroutine), not `bot.run()` (blocking) when co-running with WS server. [VERIFIED: CLAUDE.md]
- **Global command sync:** Takes up to 1 hour to propagate. Always use guild-scoped sync for development and small-scale bots. [VERIFIED: discord.py docs]
- **Prefix commands alongside slash commands:** D-04 explicitly forbids prefix commands. Only use `app_commands`. [VERIFIED: CONTEXT.md]
- **`message_content` intent:** Not needed since all interaction is via slash commands. Requesting it triggers Discord review for verified bots. [VERIFIED: CONTEXT.md D-19]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slash command registration | Manual HTTP API calls | `bot.tree.sync(guild=...)` | discord.py handles command tree, deduplication, and Discord API sync |
| Permission enforcement | Manual middleware | `app_commands.check()` or `interaction_check()` | Built-in check system with proper error handling |
| Embed formatting | Manual JSON construction | `discord.Embed()` | Type-safe, field validation, color support |
| Guild command scoping | Per-command guild filtering | `tree.copy_global_to(guild=...)` | One-time copy + sync, discord.py manages state |
| Channel creation | Discord REST API calls | `guild.create_text_channel()` | Handles permissions, position, category automatically |

**Key insight:** discord.py 2.x provides a complete `app_commands` subsystem. Every slash command operation has a first-class API -- do not call Discord REST endpoints directly.

## Common Pitfalls

### Pitfall 1: Command Tree Sync Timing
**What goes wrong:** Commands don't appear in Discord after bot starts.
**Why it happens:** `tree.sync()` called before bot is fully ready, or sync happens on wrong guild.
**How to avoid:** Always sync in `setup_hook()` (called after internal cache is ready but before `on_ready`). Sync to each guild in `allowed_guild_ids` explicitly.
**Warning signs:** Commands visible in code but not in Discord's slash command menu.

### Pitfall 2: Ephemeral Response Timing
**What goes wrong:** `interaction.response.send_message` fails with "interaction already acknowledged."
**Why it happens:** Discord requires a response within 3 seconds. If processing takes longer, must `defer()` first.
**How to avoid:** For Phase 2 commands (status/help/ping/reload), all should respond under 3s. If `/reload` reads a large file, use `await interaction.response.defer()` then `await interaction.followup.send()`.
**Warning signs:** `discord.errors.NotFound: 404 Not Found (error code: 10062): Unknown interaction`

### Pitfall 3: Channel ID as String vs Int
**What goes wrong:** Channel mapping lookup fails because JSON keys are strings but Discord channel IDs are integers.
**Why it happens:** JSON keys are always strings. `interaction.channel_id` returns `int`.
**How to avoid:** Always convert: `config.channel_mapping.get(str(interaction.channel_id))`. Store as string keys in config.json.
**Warning signs:** Agent lookup returns None despite correct mapping in config.

### Pitfall 4: Bot Missing Permissions for Channel Creation
**What goes wrong:** Auto-channel creation (D-14) fails with `discord.errors.Forbidden`.
**Why it happens:** Bot role doesn't have `manage_channels` permission in the guild.
**How to avoid:** Document required bot permissions in setup guide. Add try/except with user-friendly error logging.
**Warning signs:** Agent connects but no channel appears and no notification is sent.

### Pitfall 5: Race Condition Between WS Connect and Discord Ready
**What goes wrong:** Agent connects before Discord bot is ready, so notification can't be sent to Discord channel.
**Why it happens:** D-02 specifies WS starts first. Agent may connect before Discord cache is populated.
**How to avoid:** Queue notifications that arrive before `on_ready`, then flush them after Discord is connected. Or simply skip notification if bot is not ready yet (agent is tracked regardless).
**Warning signs:** First agent connection after bot restart has no Discord notification.

### Pitfall 6: Hiding Commands from Unauthorized Users (D-15 Limitation)
**What goes wrong:** D-15 says "slash commands are hidden from unauthorized users via Discord permissions." But Discord's permission system for slash commands is limited.
**Why it happens:** Discord only supports hiding commands via `default_permissions` (role-based) or server-level command permission overrides. User ID-level hiding is not natively supported.
**How to avoid:** Set `default_permissions` to `discord.Permissions(administrator=True)` so commands are hidden by default. Then use server settings to grant access to specific roles. Combine with `app_commands.check` for user ID enforcement as a backup. Document this limitation.
**Warning signs:** Unauthorized users can see commands but get "not authorized" error when invoking them.

## Code Examples

### Complete Bot Startup (\_\_main\_\_.py)
```python
# Source: Pattern derived from discord.py advanced_startup.py + CLAUDE.md constraints
import asyncio
from loguru import logger
from bot.config import load_bot_config
from bot.server import AgentManager
from bot.discord_bot import TerminalBot
from websockets.asyncio.server import serve

async def run():
    config = load_bot_config()
    manager = AgentManager(config)

    # WS server starts first (D-02)
    ws_server = await serve(manager.handler, config.ws_host, config.ws_port)
    logger.info(f"WebSocket server started on ws://{config.ws_host}:{config.ws_port}")

    heartbeat_task = asyncio.create_task(manager._heartbeat_loop())

    bot = TerminalBot(agent_manager=manager, config=config)

    try:
        await bot.start(config.discord_token)
    except KeyboardInterrupt:
        pass
    finally:
        # Graceful shutdown (D-03)
        heartbeat_task.cancel()
        ws_server.close()
        await ws_server.wait_closed()
        if not bot.is_closed():
            await bot.close()
        logger.info("Bot shut down complete")

def main():
    asyncio.run(run())

if __name__ == "__main__":
    main()
```

### Config Extension (config.json schema)
```json
{
    "websocket": { "host": "0.0.0.0", "port": 8765 },
    "heartbeat": { "interval_seconds": 15, "timeout_seconds": 30 },
    "auth": { "registration_timeout_seconds": 10 },
    "logging": { "level": "INFO", "file": "logs/bot.log" },
    "discord": {
        "allowed_guild_ids": [123456789],
        "allowed_user_ids": [987654321],
        "channel_mapping": {
            "111222333444": "my-desktop",
            "555666777888": "my-laptop"
        }
    }
}
```

### Embed for /status
```python
import time
import discord

def build_status_embed(agents: dict) -> discord.Embed:
    if not agents:
        embed = discord.Embed(
            title="Agent Status",
            description="No agents connected",
            color=0x95A5A6,  # Gray
        )
        return embed

    embed = discord.Embed(title="Agent Status", color=0x2ECC71)  # Green
    for name, info in agents.items():
        status_icon = "🟢"
        embed.add_field(
            name=f"{status_icon} {name}",
            value=f"**Platform:** {info.platform}\n**Status:** Online",
            inline=False,
        )
    embed.set_footer(text=f"{len(agents)} agent(s) connected")
    return embed
```

### Guild Check (AUTH-04)
```python
# In on_interaction or as a global check
@bot.tree.interaction_check
async def global_check(interaction: discord.Interaction) -> bool:
    if interaction.guild_id not in bot.bot_config.allowed_guild_ids:
        return False  # silently ignore
    if interaction.user.id not in bot.bot_config.allowed_user_ids:
        await interaction.response.send_message(
            "You are not authorized to use this bot.", ephemeral=True
        )
        return False
    return True
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| discord.py 1.x + prefix commands | discord.py 2.x + app_commands (slash) | 2022 (v2.0) | Mandatory migration to slash commands |
| Global command sync (1hr delay) | Guild-scoped sync (instant) | discord.py 2.0 | Development iteration speed |
| `bot.run()` blocking call | `bot.start()` coroutine | discord.py 2.0 | Enables co-running with other async services |
| Manual REST API for slash commands | `CommandTree` abstraction | discord.py 2.0 | Type-safe command registration |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | discord.py 2.7.1 is compatible with Python 3.13.2 | Standard Stack | Bot fails to start; would need to use virtual env with 3.12 |
| A2 | `default_permissions(administrator=True)` effectively hides commands from non-admin users | Pitfall 6 | Commands visible to everyone; only enforcement is the check decorator |
| A3 | `tree.copy_global_to()` + `sync(guild=)` works for multi-guild scenarios | Architecture Patterns | May need per-guild command registration instead |

## Open Questions

1. **D-15 Implementation Feasibility**
   - What we know: Discord's native command hiding works at role level, not user ID level. `default_permissions` can hide from non-admins.
   - What's unclear: Whether the user expects true invisibility or just rejection-on-invoke is sufficient.
   - Recommendation: Implement `default_permissions(administrator=True)` + `app_commands.check` for user ID enforcement. Document that command visibility depends on Discord server role configuration.

2. **Auto-Channel Guild Selection (D-14)**
   - What we know: When an agent connects with no channel mapped, bot creates a channel.
   - What's unclear: If there are multiple allowed guilds, which guild gets the auto-created channel?
   - Recommendation: Create in the first allowed guild, or require a `default_guild_id` in config.

3. **Config.json Write Safety**
   - What we know: `/reload` reads config.json. Auto-channel creation writes to config.json.
   - What's unclear: Race condition if both happen simultaneously.
   - Recommendation: Use `asyncio.Lock` for config.json read/write operations.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes (via `py`) | 3.13.2 | -- |
| discord.py | Discord bot | Not installed | -- | Must install: `pip install discord.py==2.7.1` |
| websockets | WS server | Yes | 16.0 | -- |
| pydantic | Validation | Yes | 2.12.5 | -- |
| Discord Bot Token | Bot auth | Not configured | -- | User must create bot at discord.com/developers |

**Missing dependencies with no fallback:**
- discord.py must be installed (add to requirements.txt)
- Discord bot token must be configured in `bot/.env`

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pytest.ini` (exists) |
| Quick run command | `py -m pytest tests/ -x -q` |
| Full suite command | `py -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ROUT-01 | Channel maps to one agent | unit | `py -m pytest tests/test_routing.py::test_channel_agent_mapping -x` | Wave 0 |
| ROUT-02 | Config file defines mapping | unit | `py -m pytest tests/test_config.py::test_discord_config_loading -x` | Partial (test_config.py exists) |
| ROUT-03 | Unmapped channels rejected | unit | `py -m pytest tests/test_routing.py::test_unmapped_channel_rejected -x` | Wave 0 |
| ROUT-04 | /help lists commands | unit | `py -m pytest tests/test_commands.py::test_help_command -x` | Wave 0 |
| ROUT-05 | Runs on user machine | manual | N/A (structural, not testable) | N/A |
| AUTH-01 | User ID allowlist | unit | `py -m pytest tests/test_auth.py::test_user_allowlist -x` | Wave 0 |
| AUTH-04 | Guild ID allowlist | unit | `py -m pytest tests/test_auth.py::test_guild_allowlist -x` | Wave 0 |
| AGNT-03 | Connect/disconnect notifications | unit | `py -m pytest tests/test_notifications.py::test_agent_notifications -x` | Wave 0 |
| AGNT-06 | /status shows agents | unit | `py -m pytest tests/test_commands.py::test_status_command -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `py -m pytest tests/ -x -q`
- **Per wave merge:** `py -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_routing.py` -- covers ROUT-01, ROUT-03
- [ ] `tests/test_commands.py` -- covers ROUT-04, AGNT-06 (mock discord.Interaction)
- [ ] `tests/test_auth.py` -- covers AUTH-01, AUTH-04
- [ ] `tests/test_notifications.py` -- covers AGNT-03
- [ ] Update `tests/test_config.py` -- extend for Discord config fields
- [ ] discord.py install: `pip install discord.py==2.7.1`

### Testing discord.py Commands
discord.py interactions are hard to unit test directly (require Discord API mocking). Recommended approach:
1. **Extract logic into pure functions** -- e.g., `build_status_embed(agents)` is testable without Discord
2. **Test routing logic separately** -- channel-to-agent lookup is a dict operation
3. **Test access control separately** -- user/guild ID checks are simple set membership tests
4. **Integration test with dpytest** -- optional; `dpytest` library can mock Discord interactions but adds complexity [ASSUMED]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | Discord OAuth (bot token) + user ID allowlist |
| V3 Session Management | No | Discord handles sessions |
| V4 Access Control | Yes | Guild ID + User ID allowlists via app_commands.check |
| V5 Input Validation | Yes | Slash command parameters are type-validated by Discord + pydantic for WS messages |
| V6 Cryptography | No | Deferred to Phase 5 (TLS/WSS) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unauthorized command execution | Elevation of Privilege | User ID allowlist check on every interaction |
| Bot token exposure | Information Disclosure | .env file, .gitignore, never log token |
| Guild spoofing | Spoofing | Guild ID allowlist, only sync commands to allowed guilds |
| Config.json tampering | Tampering | File on local machine only, no remote write access |

## Sources

### Primary (HIGH confidence)
- [discord.py PyPI](https://pypi.org/project/discord.py/) -- version 2.7.1 confirmed
- [discord.py GitHub examples](https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py) -- setup_hook, tree.sync, slash command patterns
- [discord.py advanced_startup.py](https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py) -- Bot subclass with setup_hook
- Phase 1 codebase (`bot/server.py`, `bot/config.py`, `shared/protocol.py`) -- existing patterns verified via Read tool
- `CLAUDE.md` -- tech stack decisions and anti-patterns

### Secondary (MEDIUM confidence)
- [discord.py slash command gist](https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f) -- guild sync patterns
- [Python Discord guide](https://www.pythondiscord.com/pages/guides/python-guides/app-commands/) -- app_commands patterns
- [discord.py discussions #9230](https://github.com/Rapptz/discord.py/discussions/9230) -- command permissions behavior

### Tertiary (LOW confidence)
- discord.py 2.7.1 compatibility with Python 3.13 -- not verified against release notes

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- discord.py version verified, all other deps from existing requirements.txt
- Architecture: HIGH -- patterns from official examples and existing Phase 1 code
- Pitfalls: HIGH -- well-documented in discord.py community discussions
- Access control: MEDIUM -- D-15 (command hiding) has Discord API limitations

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (discord.py is stable, 30-day validity)
