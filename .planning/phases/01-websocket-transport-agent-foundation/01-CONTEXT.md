# Phase 1: WebSocket Transport & Agent Foundation - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Bot hosts a WebSocket server; lightweight agents on remote machines connect outbound, authenticate via shared secret, register with machine info, and maintain persistent connections with heartbeat monitoring. This phase delivers the transport layer only — no Discord integration, no shell execution, no Claude Code.

</domain>

<decisions>
## Implementation Decisions

### Project Structure
- **D-01:** Monorepo with shared directory — `bot/`, `agent/`, `shared/` side by side. `shared/` contains protocol definitions, message types, and constants used by both
- **D-02:** Entry points via `python -m bot` and `python -m agent` using `__main__.py`
- **D-03:** Single `requirements.txt` for all dependencies (bot + agent combined)

### WebSocket Protocol
- **D-04:** JSON wire format with Pydantic model validation for all messages
- **D-05:** UUID `request_id` for request/response correlation
- **D-06:** Phase 1 message types: `register`, `heartbeat_ping`, `heartbeat_pong`, `ack`, `error`, `disconnect`. Command/response types added in Phase 3
- **D-07:** Heartbeat: ping every 15s, agent considered dead after 30s (2 missed pings)

### Authentication
- **D-08:** Authentication via first message — agent sends `{type: "register", secret: "...", machine_name: "...", platform: "..."}`. Bot verifies secret, responds with ack or error+close
- **D-09:** Failed auth: bot sends `{type: "error", reason: "auth_failed"}` then closes connection. Log attempt on bot side
- **D-10:** Registration timeout: 10s after WS connect. If no register message received, close connection

### Reconnection Strategy
- **D-11:** Exponential backoff: 1s → 2s → 4s → ... max 60s, with random jitter 0-1s
- **D-12:** Agent re-registers (sends register message again) after each reconnect

### Config & Environment
- **D-13:** Secrets (bot token, shared secret) in `.env` file. Settings (port, timeouts, intervals) in `config.json`
- **D-14:** Both `.env.example` and `config.example.json` provided and committed to repo

### Logging & Error Handling
- **D-15:** Use `loguru` for structured logging with color output and file rotation
- **D-16:** WS connection errors: log warning and continue. One agent failure does not affect others. Wait for reconnect

### Testing
- **D-17:** `pytest` + `pytest-asyncio` for unit tests (protocol validation) and integration tests (real WS connection on localhost)

### Registration Handshake
- **D-18:** 1-step handshake: single register message carries both auth (secret) and metadata (machine_name, platform)
- **D-19:** Registration timeout: 10s — bot closes connection if no register message within 10s of WS connect

### Network Config
- **D-20:** Default WebSocket port: 8765 (configurable in config.json)
- **D-21:** Bot binds to 0.0.0.0 (all interfaces) to accept connections from remote agents

### Concurrent Agents
- **D-22:** Machine name is unique key — second agent with same name is rejected
- **D-23:** No limit on concurrent agents (small group use case)

### Agent Metadata
- **D-24:** Agent sends `machine_name` and `platform` (win32/darwin/linux) in register message. Minimal metadata for Phase 1

### Graceful Shutdown
- **D-25:** Agent sends `{type: "disconnect"}` before shutting down. Bot distinguishes intentional disconnect from network failure

### Security
- **D-26:** Phase 1 uses plain `ws://` (no TLS). WSS can be added in hardening phase
- **D-27:** No rate limiting on connection attempts in Phase 1 — deferred to Phase 5

### Claude's Discretion
- Heartbeat direction (bot ping → agent pong, or bidirectional)
- Whether agent retries forever or gives up after max attempts
- Exact Pydantic model structure for messages
- Log file rotation settings
- Exact backoff jitter implementation

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above. The tech stack is defined in `CLAUDE.md` (project root) which specifies discord.py, websockets 12.x, asyncio, Pydantic 2.x, loguru, and python-dotenv.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None — first phase, patterns will be established here

### Integration Points
- Phase 2 will add Discord bot that uses the WebSocket server from this phase
- Phase 3 will add command/response message types to the protocol defined here

</code_context>

<specifics>
## Specific Ideas

- CLAUDE.md specifies `websockets` 12.x library and `asyncio.create_subprocess_exec` (for later phases)
- CLAUDE.md warns against `shell=True`, threading for subprocess, and running `asyncio.run()` inside discord.py's loop
- Protocol should be extensible — new message types added in later phases without breaking existing ones

</specifics>

<deferred>
## Deferred Ideas

- TLS/WSS encryption — Phase 5 hardening
- Connection rate limiting — Phase 5 hardening
- Discord notifications on agent connect/disconnect — Phase 2
- Agent status command (`/status`) — Phase 2

</deferred>

---

*Phase: 01-websocket-transport-agent-foundation*
*Context gathered: 2026-04-07*
