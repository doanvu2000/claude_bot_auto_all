# Roadmap: Discord Terminal Bot

## Overview

This roadmap delivers a Discord-based remote terminal system in five phases. We start with the WebSocket transport layer that connects agents to the bot, then wire up Discord message routing, then build shell command execution, then add Claude Code session management, and finally harden the system for unattended use. Each phase delivers a testable, coherent capability that builds on the previous one.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: WebSocket Transport & Agent Foundation** - Bot hosts WS server; agents connect, register, and maintain heartbeat
- [ ] **Phase 2: Discord Bot & Message Routing** - Bot joins Discord, routes channel messages to correct agent, enforces access control
- [ ] **Phase 3: Shell Command Execution** - Users execute shell commands on remote machines and see output in Discord
- [ ] **Phase 4: Claude Code Sessions** - Users interact with Claude Code on remote machines with persistent sessions
- [ ] **Phase 5: Hardening & Polish** - Rate limiting, process cleanup, encoding fixes for production reliability

## Phase Details

### Phase 1: WebSocket Transport & Agent Foundation
**Goal**: Bot and agents can establish authenticated, persistent, self-healing WebSocket connections with structured message passing
**Depends on**: Nothing (first phase)
**Requirements**: INFR-01, INFR-02, INFR-03, INFR-04, AGNT-01, AGNT-02, AGNT-04, AGNT-05, AUTH-02, AUTH-03
**Success Criteria** (what must be TRUE):
  1. Agent process can connect to bot's WebSocket server and complete a registration handshake including machine name and platform info
  2. Bot rejects agent connections that do not provide the correct shared secret
  3. When agent's network drops, it automatically reconnects with exponential backoff and re-registers without manual intervention
  4. Bot and agent exchange periodic heartbeat pings; bot detects a dead agent within 30 seconds of disconnection
  5. Bot and agent config files load from JSON/env with example templates available
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — WebSocket server and agent authentication
- [x] 01-02-PLAN.md — Agent client with reconnection logic
- [x] 01-03-PLAN.md — Heartbeat monitoring and graceful shutdown

### Phase 2: Discord Bot & Message Routing
**Goal**: Users in Discord can send messages that reach the correct machine agent, with access control enforced and agent status visible
**Depends on**: Phase 1
**Requirements**: ROUT-01, ROUT-02, ROUT-03, ROUT-04, ROUT-05, AUTH-01, AUTH-04, AGNT-03, AGNT-06
**Success Criteria** (what must be TRUE):
  1. Messages sent in a mapped Discord channel are delivered to the correct agent based on channel-to-agent config
  2. Messages from unauthorized users (not on allowlist) or unauthorized guilds are rejected with no command execution
  3. Messages in unmapped channels are silently ignored
  4. When an agent connects or disconnects, a notification appears in its mapped Discord channel
  5. User can run `/status` to see all connected agents and `/help` to see available commands
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md — Bot infrastructure: config extension, TerminalBot class, dual WS+Discord startup, AgentManager callbacks
- [ ] 02-02-PLAN.md — Slash commands (/status, /help, /ping, /reload), access control, agent notifications, auto-channel creation
- [ ] 02-03-PLAN.md — Unit tests for routing, config, auth, commands, and notifications

### Phase 3: Shell Command Execution
**Goal**: Users can execute shell commands on any connected machine via Discord and receive formatted output
**Depends on**: Phase 2
**Requirements**: EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05, EXEC-06, EXEC-07, EXEC-08, EXEC-09
**Success Criteria** (what must be TRUE):
  1. User types a shell command in a mapped channel; the command executes on the target machine and output appears in Discord as a code block with exit code and duration
  2. Output exceeding 2000 characters is truncated in-message with the full output uploaded as a file attachment
  3. Working directory persists across messages (running `cd /tmp` then `pwd` in subsequent message shows `/tmp`)
  4. Commands exceeding 90s timeout are killed automatically with a notification; user can also kill a running command via `/kill`
  5. Multi-line code blocks pasted in Discord execute as a single script; command receipt is acknowledged immediately with a reaction
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD
- [ ] 03-03: TBD

### Phase 4: Claude Code Sessions
**Goal**: Users can interact with Claude Code on remote machines through Discord with persistent, resumable sessions
**Depends on**: Phase 3
**Requirements**: CLDE-01, CLDE-02, CLDE-03, CLDE-04, CLDE-05, CLDE-06
**Success Criteria** (what must be TRUE):
  1. User can send a prompt to Claude Code on the target machine and receive the response in Discord
  2. Claude session maintains context across multiple messages -- a follow-up prompt references previous conversation
  3. Session ID is persisted to disk; after bot or agent restart, the next prompt resumes the same session
  4. User can run `/new-session` to start a fresh Claude session and `/claude` or `/shell` to toggle between modes
  5. If a Claude session is stale or dead, the system automatically starts a new session and notifies the user
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD

### Phase 5: Hardening & Polish
**Goal**: System runs reliably unattended with protection against abuse, zombie processes, and encoding issues
**Depends on**: Phase 4
**Requirements**: AUTH-05, INFR-05, INFR-06
**Success Criteria** (what must be TRUE):
  1. Rapid command submissions from a single user are rate-limited with feedback rather than silently queued or executed
  2. When a command is killed or times out, all child processes are also terminated (no zombie/orphan processes remain)
  3. Commands producing non-ASCII output on Windows return correctly encoded text in Discord (no mojibake)
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. WebSocket Transport & Agent Foundation | 0/3 | Not started | - |
| 2. Discord Bot & Message Routing | 0/3 | Not started | - |
| 3. Shell Command Execution | 0/3 | Not started | - |
| 4. Claude Code Sessions | 0/3 | Not started | - |
| 5. Hardening & Polish | 0/2 | Not started | - |
