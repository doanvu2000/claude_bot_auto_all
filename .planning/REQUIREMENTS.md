# Requirements: Discord Terminal Bot

**Defined:** 2026-04-06
**Core Value:** From any Discord client, control any registered machine's terminal and Claude Code — without opening SSH or switching apps.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Shell Execution

- [ ] **EXEC-01**: User can execute arbitrary shell commands on target machine via Discord message
- [ ] **EXEC-02**: Command output returned to Discord in code blocks with exit code and duration
- [ ] **EXEC-03**: Output exceeding 2000 chars is truncated with notice + full output uploaded as file attachment
- [ ] **EXEC-04**: Working directory persists across messages per channel session (cd sticks)
- [ ] **EXEC-05**: Commands timeout after 90s (configurable) with notification
- [ ] **EXEC-06**: User can kill a running command via `/kill`
- [ ] **EXEC-07**: Cross-platform shell support (PowerShell on Windows, bash/zsh on macOS)
- [ ] **EXEC-08**: Immediate acknowledgment (reaction) when command is received before execution starts
- [ ] **EXEC-09**: Multi-line command blocks (Discord code blocks) run as single script

### Claude Code Sessions

- [ ] **CLDE-01**: User can send prompts to Claude Code on target machine and receive response in Discord
- [ ] **CLDE-02**: Claude session persists across messages — context maintained between prompts
- [ ] **CLDE-03**: Session ID persisted to disk — survives bot and agent restarts
- [ ] **CLDE-04**: `/new-session` command resets Claude session for current channel
- [ ] **CLDE-05**: Stale/dead session detected automatically — falls back to new session with notification
- [ ] **CLDE-06**: Mode toggle via `/claude` and `/shell` to switch between Claude and shell mode

### Access Control & Security

- [ ] **AUTH-01**: Discord user ID allowlist enforced on every command execution
- [ ] **AUTH-02**: Agent authenticates to bot via shared secret on WebSocket connection
- [ ] **AUTH-03**: Credentials stored in `.env` file, never hardcoded
- [ ] **AUTH-04**: Guild (server) ID allowlist — bot rejects unauthorized Discord servers
- [ ] **AUTH-05**: Rate limiting per user to prevent command flooding

### Agent Management

- [ ] **AGNT-01**: Each machine runs a lightweight Python agent connecting to bot via WebSocket
- [ ] **AGNT-02**: Agent registers with machine name and platform info on connection
- [ ] **AGNT-03**: Machine online/offline status displayed in Discord when agent connects/disconnects
- [ ] **AGNT-04**: Agent auto-reconnects with exponential backoff + jitter after disconnect
- [ ] **AGNT-05**: Heartbeat ping/pong between bot and agent for connection health monitoring
- [ ] **AGNT-06**: `/status` command shows all connected agents and their state

### Bot & Routing

- [ ] **ROUT-01**: Each Discord channel maps to exactly one machine (channel-per-machine routing)
- [ ] **ROUT-02**: Channel-to-agent mapping configured via static config file (channel IDs)
- [ ] **ROUT-03**: Messages in unmapped channels are ignored silently
- [ ] **ROUT-04**: `/help` command lists all available bot commands
- [ ] **ROUT-05**: Bot runs on user's own machine — no VPS required

### Infrastructure

- [ ] **INFR-01**: Bot hosts WebSocket server for agent connections
- [ ] **INFR-02**: JSON wire protocol with request_id correlation for async command/response matching
- [ ] **INFR-03**: Bot and agent share protocol definitions (monorepo structure)
- [ ] **INFR-04**: Config files for bot (config.json) and agent (agent.json) with examples
- [ ] **INFR-05**: Process group kill on timeout/cancel (handles child processes, not just parent)
- [ ] **INFR-06**: UTF-8 encoding handling for Windows subprocess output

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced UX

- **UX-01**: Command history per channel (`/history`)
- **UX-02**: Command aliases (define shortcuts for common commands)
- **UX-03**: Startup commands per machine (auto-run on agent connect)
- **UX-04**: Session context summary ("current session info")
- **UX-05**: Streaming output (real-time edit of Discord message as output grows)

### Advanced Execution

- **ADV-01**: Stdin / interactive command support (`/stdin` to send input to running process)
- **ADV-02**: Per-machine environment variables
- **ADV-03**: Per-command timeout override

## Out of Scope

| Feature | Reason |
|---------|--------|
| Telegram support | Discord only for v1 — simplicity |
| Web dashboard / GUI | Discord IS the UI |
| Cloud/VPS hosting | Bot runs on user's own hardware |
| Public/open access | Controlled group only — security |
| SSH tunneling | WebSocket agent model is simpler |
| Database for state | JSON files sufficient at this scale |
| OAuth / Discord role-based auth | User ID allowlist is sufficient for small group |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXEC-01 | — | Pending |
| EXEC-02 | — | Pending |
| EXEC-03 | — | Pending |
| EXEC-04 | — | Pending |
| EXEC-05 | — | Pending |
| EXEC-06 | — | Pending |
| EXEC-07 | — | Pending |
| EXEC-08 | — | Pending |
| EXEC-09 | — | Pending |
| CLDE-01 | — | Pending |
| CLDE-02 | — | Pending |
| CLDE-03 | — | Pending |
| CLDE-04 | — | Pending |
| CLDE-05 | — | Pending |
| CLDE-06 | — | Pending |
| AUTH-01 | — | Pending |
| AUTH-02 | — | Pending |
| AUTH-03 | — | Pending |
| AUTH-04 | — | Pending |
| AUTH-05 | — | Pending |
| AGNT-01 | — | Pending |
| AGNT-02 | — | Pending |
| AGNT-03 | — | Pending |
| AGNT-04 | — | Pending |
| AGNT-05 | — | Pending |
| AGNT-06 | — | Pending |
| ROUT-01 | — | Pending |
| ROUT-02 | — | Pending |
| ROUT-03 | — | Pending |
| ROUT-04 | — | Pending |
| ROUT-05 | — | Pending |
| INFR-01 | — | Pending |
| INFR-02 | — | Pending |
| INFR-03 | — | Pending |
| INFR-04 | — | Pending |
| INFR-05 | — | Pending |
| INFR-06 | — | Pending |

**Coverage:**
- v1 requirements: 37 total
- Mapped to phases: 0
- Unmapped: 37 ⚠️

---
*Requirements defined: 2026-04-06*
*Last updated: 2026-04-06 after initial definition*
