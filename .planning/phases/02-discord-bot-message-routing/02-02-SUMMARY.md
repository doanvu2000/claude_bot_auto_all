---
phase: 02-discord-bot-message-routing
plan: 02
subsystem: discord-commands
tags: [slash-commands, access-control, auto-channel, notifications]
dependency_graph:
  requires: [02-01]
  provides: [general-cog, slash-commands, auto-channel-creation]
  affects: [bot/cogs/general.py, bot/discord_bot.py]
tech_stack:
  added: []
  patterns: [cog-based-commands, interaction-check-auth, embed-responses]
key_files:
  created:
    - bot/cogs/__init__.py
    - bot/cogs/general.py
  modified:
    - bot/discord_bot.py
decisions:
  - interaction_check is PRIMARY auth gate; default_permissions is UI hiding only
  - /status shows three agent states (connected-mapped, connected-unmapped, offline-configured)
  - Auto-channel uses first allowed guild when agent has no mapping
  - Duplicate channel prevention by name matching before creation
metrics:
  duration: 154s
  completed: 2026-04-07T17:01:00Z
  tasks: 2/2
  files_created: 2
  files_modified: 1
---

# Phase 02 Plan 02: Slash Commands and Agent Notifications Summary

GeneralCog with /status, /help, /ping, /reload using embed responses, dual-layer auth (interaction_check primary + default_permissions UI hiding), auto-channel creation with duplicate prevention and config.json persistence.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create GeneralCog with slash commands and access control | 6f5b139 | bot/cogs/__init__.py, bot/cogs/general.py |
| 2 | Agent notifications and auto-channel creation | 2a6c9a9 | bot/discord_bot.py |

## Implementation Details

### Task 1: GeneralCog Slash Commands
- Created `bot/cogs/general.py` with `GeneralCog(commands.Cog)` class
- `interaction_check` as PRIMARY security gate: checks guild allowlist (AUTH-04) and user allowlist (AUTH-01)
- `@app_commands.default_permissions(administrator=True)` as UI hiding only (defense-in-depth)
- `/status` shows connected agents (green, mapped/unmapped), offline configured agents (red), with embed
- `/help` lists all 4 commands as embed fields
- `/ping` returns bot WebSocket latency in ms
- `/reload` calls async `reload_config()` (lock-protected) then re-syncs commands to guilds

### Task 2: Auto-Channel Creation and Notifications
- Completed `_on_agent_connect` stub: calls `_auto_create_channel` when no mapping exists
- `_auto_create_channel` sanitizes machine name, checks for duplicate channel names, creates text channel in first allowed guild
- Updates `channel_mapping` and persists via `save_config()` (lock-protected)
- Handles `discord.Forbidden` when bot lacks manage_channels permission
- All `channel.send()` calls wrapped in try/except (review concern #6)

## Decisions Made

1. **Auth model**: `interaction_check` is the real enforcement; `default_permissions` is cosmetic Discord UI hiding
2. **Three-state /status**: Shows connected-mapped, connected-unmapped (no channel), and offline-configured agents
3. **Auto-channel guild**: Uses `allowed_guild_ids[0]` for auto-creation (per RESEARCH resolution)
4. **Duplicate prevention**: Checks `guild.text_channels` by name before creating; maps to existing if found

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

- `from bot.cogs.general import GeneralCog` -- OK
- `from bot.discord_bot import TerminalBot` -- OK
- All 4 slash commands present with correct signatures
- `interaction_check` docstring contains "PRIMARY security gate"
- `_auto_create_channel` with duplicate prevention, `discord.Forbidden` handling
- `_on_agent_connect` and `_on_agent_disconnect` both have try/except
- 55 tests pass (pytest)

## Self-Check: PASSED

All created files exist on disk. All commit hashes verified in git log.
