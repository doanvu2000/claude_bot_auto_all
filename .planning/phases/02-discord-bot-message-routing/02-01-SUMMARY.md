---
phase: 02-discord-bot-message-routing
plan: 01
subsystem: discord-bot-core
tags: [discord, routing, config, websocket, callbacks]
dependency_graph:
  requires: [phase-01-websocket-transport]
  provides: [TerminalBot, BotConfig-discord, routing-api, agent-callbacks]
  affects: [bot/config.py, bot/server.py, bot/__main__.py]
tech_stack:
  added: [discord.py==2.7.1]
  patterns: [asyncio.Lock for config concurrency, guild interaction_check for AUTH-04, callback pattern for agent lifecycle]
key_files:
  created:
    - bot/discord_bot.py
    - bot/.env.example
    - config.json
  modified:
    - bot/config.py
    - bot/server.py
    - bot/__main__.py
    - shared/constants.py
    - requirements.txt
    - tests/conftest.py
    - tests/test_config.py
decisions:
  - BotConfig converted from dataclass to regular class to support asyncio.Lock and methods
  - Shared _config_lock used by both save_config and reload_config to prevent concurrent read/write
  - Runtime guild allowlist enforcement via global_interaction_check (AUTH-04 defense-in-depth layer 2)
  - WS server starts before Discord bot in entry point (D-02)
  - Discord LoginFailure triggers clean shutdown, no degraded mode (D-03, review concern #7)
metrics:
  duration: 509s
  completed: "2026-04-07"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 10
requirements: [ROUT-01, ROUT-02, ROUT-05, AUTH-04]
---

# Phase 02 Plan 01: Discord Bot Core Infrastructure Summary

Extended BotConfig with Discord token, channel mapping, guild/user allowlists, and lock-protected save/reload; created TerminalBot with routing API (get_agent_for_channel, _find_channel_for_agent) and AgentManager lifecycle callbacks.

## Task Results

### Task 1: Extend config, env, and dependencies for Discord
**Commit:** cb7cc98
**Files:** bot/config.py, shared/constants.py, requirements.txt, bot/.env.example, config.json, tests/conftest.py, tests/test_config.py

- Added discord.py==2.7.1 dependency
- Added DEFAULT_DISCORD_COMMAND_PREFIX to shared/constants.py
- Created bot/.env.example with DISCORD_BOT_TOKEN placeholder
- Created config.json with discord section (allowed_guild_ids, allowed_user_ids, channel_mapping)
- Converted BotConfig from @dataclass to regular class with __init__ to support asyncio.Lock
- Added fields: discord_token, allowed_guild_ids, allowed_user_ids, channel_mapping, config_path
- Added async save_config() - re-reads full JSON, updates only channel_mapping, writes back
- Added async reload_config() - updates mutable fields, skips discord_token
- Both methods share self._config_lock (asyncio.Lock) to prevent concurrent read/write
- Updated existing tests to provide DISCORD_BOT_TOKEN env var
- Added tests for missing token validation and Discord config loading

### Task 2: Create TerminalBot with routing API, rewrite entry point, add AgentManager callbacks
**Commit:** 7253f9b
**Files:** bot/discord_bot.py, bot/server.py, bot/__main__.py

- Created bot/discord_bot.py with TerminalBot(commands.Bot) class
- Routing API: get_agent_for_channel(channel_id) returns machine_name for a Discord channel
- Routing API: _find_channel_for_agent(machine_name) returns channel_id for a machine (reverse lookup)
- setup_hook syncs slash commands to allowed guilds (defense-in-depth layer 1)
- global_interaction_check rejects unauthorized guilds at runtime (AUTH-04, layer 2)
- Agent connect/disconnect notifications sent to mapped channels with try/except isolation
- Added on_agent_connect and on_agent_disconnect callback attributes to AgentManager
- Callbacks fired in _authenticate (connect) and _remove_agent (disconnect) with exception isolation
- Rewrote bot/__main__.py: WS server starts first (D-02), then Discord bot
- Handles discord.LoginFailure for clean shutdown (review concern #7, D-03)
- Graceful shutdown cancels heartbeat, closes WS server, closes Discord bot

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- `from bot.discord_bot import TerminalBot` - OK
- `from bot.config import load_bot_config` - OK (with env vars)
- `py -m pytest tests/ -x -q` - 55 passed
- config.json contains discord section with all three keys - OK
- bot/.env.example exists with DISCORD_BOT_TOKEN placeholder - OK
- requirements.txt contains discord.py==2.7.1 - OK
- `grep -c "_config_lock" bot/config.py` returns 6 (>= 3) - OK
- `grep -c "ROUTING API" bot/discord_bot.py` returns 2 (>= 2) - OK

## Known Stubs

- bot/discord_bot.py `_on_agent_connect`: D-14 auto-channel creation is a `pass` placeholder (resolved in Plan 02)
- bot/discord_bot.py `setup_hook`: `bot.cogs.general` extension load will fail until Plan 02 creates it (logged as warning, non-blocking)

## Threat Flags

None - all security surfaces match the plan's threat model.

## Self-Check: PASSED

All 10 files verified present. Both commit hashes (cb7cc98, 7253f9b) verified in git log.
