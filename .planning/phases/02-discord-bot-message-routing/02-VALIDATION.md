---
phase: 02
slug: discord-bot-message-routing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | ROUT-01 | — | Channel-to-agent routing delivers to correct agent | unit | `python -m pytest tests/test_discord_bot.py -k test_channel_routing -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | AUTH-01 | T-02-01 | Unauthorized users rejected | unit | `python -m pytest tests/test_discord_bot.py -k test_access_control -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | AUTH-04 | T-02-02 | Unauthorized guilds rejected | unit | `python -m pytest tests/test_discord_bot.py -k test_guild_allowlist -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | ROUT-03 | — | Unmapped channels silently ignored | unit | `python -m pytest tests/test_discord_bot.py -k test_unmapped_channel -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | AGNT-03 | — | Agent connect/disconnect notification in channel | integration | `python -m pytest tests/test_discord_bot.py -k test_agent_notification -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | ROUT-04, ROUT-05 | — | /status and /help slash commands work | integration | `python -m pytest tests/test_discord_bot.py -k test_slash_commands -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | AGNT-06 | — | /reload hot-reloads config | integration | `python -m pytest tests/test_discord_bot.py -k test_reload -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_discord_bot.py` — stubs for ROUT-01, ROUT-02, ROUT-03, ROUT-04, ROUT-05, AUTH-01, AUTH-04, AGNT-03, AGNT-06
- [ ] `tests/conftest.py` — shared fixtures (mock Discord client, mock AgentManager)
- [ ] `pip install pytest pytest-asyncio dpytest` — test framework + discord.py test utilities

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Auto-channel creation in real Discord guild | ROUT-02 | Requires live Discord API + guild permissions | 1. Connect agent with no mapped channel 2. Verify channel created in guild 3. Verify config.json updated |
| Slash command visibility/hiding for unauthorized users | AUTH-01 | Discord permission system requires real guild roles | 1. Log in as unauthorized user 2. Verify slash commands not visible in channel |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
