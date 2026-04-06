# Discord Terminal Bot

## What This Is

A Discord bot that acts as a remote control interface for multiple computers. Each Discord channel maps to one machine; messages sent in a channel execute shell commands or drive Claude Code sessions on that machine. A lightweight agent process running on each computer relays commands and streams output back to Discord.

## Core Value

From any Discord client, control any registered machine's terminal and Claude Code — without opening SSH or switching apps.

## Requirements

### Validated

- [x] Bot and agents reconnect automatically after disconnect — Validated in Phase 1: websocket-transport-agent-foundation
- [x] Agents register themselves (with machine name) when they come online — Validated in Phase 1: websocket-transport-agent-foundation

### Active

- [ ] Discord bot reads commands from channels and routes them to the correct machine
- [ ] Each Discord channel is mapped to exactly one machine agent
- [ ] Machine agent executes arbitrary shell commands and returns output to Discord
- [ ] Machine agent can drive Claude Code via `claude -p` with session continuity
- [ ] Claude Code sessions persist across messages until `/new-session` resets them
- [ ] Small-group access control — only authorized users in the server can send commands
- [ ] Bot and agents reconnect automatically after disconnect
- [ ] Agents register themselves (with machine name) when they come online

### Out of Scope

- Telegram support — Discord only for v1
- Public/open access — controlled group only
- Streaming output (real-time edit) — full output reply for v1
- Web dashboard or GUI — Discord IS the UI
- Cloud/VPS hosting — bot runs on one of the user's machines

## Context

- Bot runs on one of the user's own machines (Windows or Mac), not a cloud server
- Each additional machine runs a lightweight agent that connects back to the bot
- Claude Code CLI (`claude`) must be installed and authenticated on each machine
- Shell command execution must work cross-platform (Windows cmd/PowerShell, Mac bash/zsh)
- Session IDs from `claude --resume` or similar mechanism used to maintain Claude context
- Tech stack: AI-chosen (likely Python for simplicity — discord.py + subprocess)

## Constraints

- **Platform**: Discord only — no Telegram in v1
- **Hosting**: Runs on user's own hardware, no VPS required
- **Auth**: Discord server/channel membership as access boundary
- **Claude**: Requires `claude` CLI available on each machine
- **OS**: Must support Windows and macOS

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python stack (discord.py) | Excellent subprocess control, mature library, cross-platform | — Pending |
| Channel-per-machine routing | Simpler UX than commands, no `/target` syntax needed | — Pending |
| Agent ↔ Bot via WebSocket | Agents behind NAT — they connect OUT to bot, not the other way | — Pending |
| Session persistence via claude `--resume` | Keep context without maintaining a long-running subprocess | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-06 after initialization*
