# Project Research Summary

**Project:** Discord Terminal Bot (bot_auto_all)
**Domain:** Remote terminal control + AI session management via Discord
**Researched:** 2026-04-06
**Confidence:** MEDIUM-HIGH (all research from training data, cutoff Aug 2025; no live web verification)

## Executive Summary

This project is a multi-machine remote terminal system operated through Discord. The architecture is a hub-and-spoke model: a central Discord bot process hosts a WebSocket server, and lightweight agents on each target machine connect outbound to the bot. Users type shell commands or Claude Code prompts in per-machine Discord channels, the bot routes them to the correct agent, and results are posted back. The entire system is Python-based -- discord.py for the Discord layer, the `websockets` library for agent communication, and `asyncio` subprocess APIs for command execution. This is a well-understood topology with no novel technical risk.

The recommended approach is to build the WebSocket transport layer first (bot-to-agent plumbing), then layer Discord integration and shell execution on top, then add Claude Code session management as a third phase. This ordering front-loads the hardest architectural decision (agent communication) and validates NAT traversal assumptions before adding feature complexity. Security (user ID allowlisting, agent authentication) must be woven in during hardening but the auth check itself is trivially simple -- the real risk is forgetting to add it.

The primary risks are: (1) missing the Discord `MESSAGE_CONTENT` privileged intent, which silently breaks the bot with no error; (2) no authorization gate on command execution, which turns the bot into an open RCE vector; (3) Claude Code CLI flag instability, since `--resume` and `--output-format json` are not guaranteed stable across CLI versions; and (4) long-running commands blocking the agent if synchronous subprocess calls are used instead of async. All four are well-understood and preventable with the patterns documented in the research files.

## Key Findings

### Recommended Stack

Python throughout -- bot, agent, and shared protocol. discord.py 2.3.x for the Discord gateway, `websockets` 12.x for agent transport, `asyncio.create_subprocess_exec` for shell and Claude CLI invocation. Supporting libraries: `python-dotenv` for secrets, `pydantic` for message validation, `loguru` for structured logging. No database needed; session state is a JSON file on each agent machine, channel-to-agent mapping is a static config file on the bot.

**Core technologies:**
- **discord.py 2.3.x**: Discord bot framework -- async-native, actively maintained, supports required intents and slash commands
- **websockets 12.x**: Agent-to-bot transport -- agents connect outbound (NAT-friendly), persistent bidirectional connection, no broker needed
- **asyncio subprocess**: Shell/Claude command execution -- non-blocking, cross-platform, timeout enforcement built-in
- **Python 3.11+ (prefer 3.12)**: Runtime -- required for asyncio performance improvements and better subprocess error handling

**Critical version note:** Verify exact latest versions of discord.py and websockets on PyPI before pinning. Do not use Python 3.13 yet (C extension ecosystem lag as of mid-2025).

### Expected Features

**Must have (table stakes):**
- Shell command execution with cross-platform support (Windows cmd/PowerShell + macOS bash/zsh)
- Working directory persistence per channel session (cd must stick)
- Output returned to Discord with explicit truncation notices (never silently drop)
- Code block formatting for all command output
- Command timeout (30s default) with `/kill` to cancel
- Immediate acknowledgment of command receipt (reaction or brief reply)
- Discord user ID allowlist enforced on every execution path
- Guild ID allowlist (bot refuses unauthorized servers)
- Machine online/offline status notification
- Agent auto-reconnect with exponential backoff
- Claude Code session management (`/new-session`, session ID persistence to disk)
- `/status` command showing agent connection state
- Output file upload for large outputs exceeding Discord's 2000-char limit

**Should have (differentiators):**
- Claude Code session continuity across bot restarts (disk persistence)
- Agent heartbeat with periodic "still running" feedback for long commands
- Multi-line command blocks (paste a script, run atomically)
- Output chunking across multiple messages with chunk numbering
- Session context summary ("You are in session X, last message Y ago")

**Defer (v2+):**
- Stdin / interactive command support (high complexity)
- Command history (`/history`)
- Command aliases
- Per-machine environment variable injection
- Startup commands per machine
- Streaming output (edit-in-place) -- explicitly out of scope per PROJECT.md
- Mode toggle (Claude vs shell) -- design decision deferred

### Architecture Approach

Hub-and-spoke: one bot process with a WebSocket server, N agent processes connecting outbound. The bot maps Discord channels to agents via static config. Commands flow Discord -> ChannelRouter -> AgentRegistry -> WebSocket -> Agent Dispatcher -> ShellExecutor or ClaudeExecutor. Results flow back the same path with `request_id` correlation. All communication is JSON over WebSocket. Agent is authoritative for its own state (working directory, Claude session ID). Bot is stateless except for live connection registry.

**Major components:**

Bot side:
1. **DiscordClient** -- receives Discord messages, sends formatted replies
2. **ChannelRouter** -- maps channel_id to agent_id via static config
3. **AgentRegistry** -- tracks live WebSocket connections by agent_id
4. **MessageBroker** -- glues Discord events to agent commands; holds pending `asyncio.Future` per request_id
5. **WsServer** -- WebSocket server with shared-secret authentication

Agent side:
1. **WsClient** -- outbound WebSocket connection with exponential backoff reconnect
2. **Dispatcher** -- routes incoming commands to ShellExecutor or ClaudeExecutor by message type
3. **ShellExecutor** -- async subprocess with timeout, cross-platform shell detection
4. **ClaudeExecutor** -- invokes `claude -p --resume <id>`, manages session ID lifecycle
5. **SessionStore** -- reads/writes sessions.json on disk

### Critical Pitfalls

1. **No authorization gate** -- Any Discord server member can execute shell commands if user ID allowlist is not enforced. Check `message.author.id` against allowlist on every command. This is the single most important security control.

2. **Missing MESSAGE_CONTENT privileged intent** -- Bot silently receives empty message content with no error. Must enable in both Discord Developer Portal AND in code (`intents.message_content = True`). Document this prominently in setup instructions.

3. **Synchronous subprocess blocking the event loop** -- Using `subprocess.run()` instead of `asyncio.create_subprocess_exec` freezes the agent (and can cause Discord heartbeat misses on the bot). Use async subprocess everywhere, no exceptions.

4. **Claude session ID staleness** -- `--resume` with an invalid/expired session ID may fail silently or hang. Wrap every invocation with exit code + output validation; auto-fallback to new session with user notification.

5. **Discord 2000-char message limit** -- Attempting to send longer messages returns HTTP 400. Must truncate/chunk all output. For large outputs (>10KB), use file attachment instead of multiple messages to avoid rate limits and ordering issues.

## Implications for Roadmap

### Phase 1: WebSocket Transport + Agent Registration
**Rationale:** This is the foundational infrastructure that everything else depends on. Building it first validates the NAT traversal assumption and the agent-connects-outbound topology before adding any Discord complexity.
**Delivers:** Bot WS server, agent WS client with reconnect + backoff, registration handshake with shared-secret auth, config loading for both bot and agent.
**Addresses:** Machine online/offline detection, agent auto-reconnect.
**Avoids:** Reconnection storms (Pitfall 9) by implementing exponential backoff with jitter from day one.

### Phase 2: Discord Integration + Shell Execution
**Rationale:** This delivers the core value proposition -- type a command in Discord, see the result. Depends on Phase 1's transport layer.
**Delivers:** discord.py client with MESSAGE_CONTENT intent, ChannelRouter, MessageBroker, ShellExecutor with async subprocess, output formatting (code blocks, truncation, file upload), command timeout + `/kill`.
**Addresses:** Shell execution, working directory persistence, output handling, command timeout, `/kill`, `/status`, `/help`.
**Avoids:** Missing intents (Pitfall 12), synchronous blocking (Pitfall 5), silent output truncation (Pitfall 6), zombie processes (Pitfall 8).
**Note:** User ID allowlist must be enforced here -- not deferred to a later hardening phase.

### Phase 3: Claude Code Session Management
**Rationale:** Depends on Phase 2's command dispatch infrastructure. Claude CLI flag behavior must be verified against the installed version -- isolating this to its own phase limits blast radius if flags differ from expectations.
**Delivers:** ClaudeExecutor, SessionStore (disk-persisted), `/new-session` command, session expiry handling, auto-fallback on stale sessions.
**Addresses:** Claude Code sessions, session persistence, `/new-session`.
**Avoids:** Session state loss (Pitfall 4), CLI output format breakage (Pitfall 15).
**Research flag:** Needs verification of `claude --resume`, `--output-format json`, and session ID field name against installed CLI.

### Phase 4: Hardening + Polish
**Rationale:** Correctness before polish. This phase hardens what already works.
**Delivers:** Rate limit awareness for chunked output, guild ID allowlist, agent platform reporting in registration, Windows encoding fixes (force UTF-8 in PowerShell), process group kill for orphan cleanup, per-command timeout configuration, improved error messages with machine name + command + stderr.
**Addresses:** Cross-platform shell differences (Pitfall 10), Windows encoding (Pitfall 17), zombie processes (Pitfall 8), Discord rate limits (Pitfall 7).
**Avoids:** Message ordering issues (Pitfall 11) by using sequential await + chunk numbering.

### Phase 5: Packaging + Setup Experience
**Rationale:** Write setup docs and config templates after the design is settled, not before.
**Delivers:** `config.example.json`, `agent.example.json`, startup scripts (.bat for Windows, .sh for macOS), requirements.txt / requirements-agent.txt, README with Discord Developer Portal setup walkthrough (intents, permissions, bot invite URL).
**Addresses:** First-time setup success, documentation of port forwarding requirement for remote agents.

### Phase Ordering Rationale

- Phases 1-2 form the critical path: transport then core feature. Neither is useful without the other, but building transport in isolation is testable without Discord credentials.
- Phase 3 is isolated because Claude CLI behavior is the least certain part of the stack. If `--resume` works differently than expected, only Phase 3 needs rework.
- Phase 4 is hardening, not new features. It addresses pitfalls that matter for leaving the system running unattended but are not blockers for development use.
- Phase 5 is last because packaging before stability creates churn.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Claude Code sessions):** Claude CLI flags (`--resume`, `--output-format json`, session ID field name) must be verified against installed version. Run `claude --help` and test a round-trip invocation before writing the executor.
- **Phase 2 (Shell execution):** Windows-specific subprocess behavior (ProactorEventLoop, encoding, process group kill) should be tested on a real Windows machine early.

Phases with standard patterns (skip additional research):
- **Phase 1 (WebSocket transport):** Well-documented pattern. websockets library examples cover this exact topology.
- **Phase 4 (Hardening):** All mitigations are documented in PITFALLS.md with specific code patterns.
- **Phase 5 (Packaging):** Standard Python project packaging, no research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | discord.py and websockets are stable; exact latest versions need PyPI check |
| Features | HIGH | Table stakes derived from well-established chat terminal bot patterns |
| Architecture | HIGH | Hub-and-spoke with WebSocket is the obvious correct topology for this scale |
| Pitfalls | HIGH | Discord API limits and subprocess behavior are well-documented and stable |

**Overall confidence:** MEDIUM-HIGH

The only area of genuine uncertainty is the Claude Code CLI interface (`--resume` flag, JSON output format, session ID extraction). Everything else uses mature, stable APIs with established patterns.

### Gaps to Address

- **Claude CLI flag verification:** Run `claude --help` on each target machine at implementation time. Confirm `--resume`, `--output-format json`, and the exact JSON key for session ID. This is the highest-priority gap.
- **Claude CLI error behavior:** What happens when `--resume` receives an invalid session ID? Does it error, start fresh, or hang? Must be tested manually before writing ClaudeExecutor.
- **Shell mode UX decision:** The FEATURES.md identified a design fork -- mode toggle (Claude vs shell) vs per-message prefix. This must be decided before Phase 2/3 implementation. Recommendation: start with per-message prefix (`>` for Claude, plain for shell) as it requires no state and is easier to implement.
- **Port exposure for remote agents:** If agents are on different networks from the bot, the bot machine needs port forwarding. This is an ops concern but should be documented in Phase 5. Consider optional ngrok/Cloudflare Tunnel support as a future enhancement.
- **discord.py and websockets version pinning:** Check PyPI for current stable versions before writing requirements.txt.

## Sources

### Primary (HIGH confidence)
- Python asyncio subprocess docs: https://docs.python.org/3/library/asyncio-subprocess.html
- Discord Developer Docs (intents, rate limits, message limits): https://discord.com/developers/docs
- discord.py library: https://discordpy.readthedocs.io/en/stable/
- websockets library: https://websockets.readthedocs.io/

### Secondary (MEDIUM confidence)
- discord.py 2.3.x current status (training data, Aug 2025 cutoff)
- websockets 12.x API stability (training data)
- Chat terminal bot UX patterns (Telegram termbot, IRC shellbot ecosystems)

### Tertiary (LOW confidence -- verify at implementation time)
- Claude Code CLI flags: `--resume`, `--output-format json`, `--no-permissions-prompt`
- Claude CLI session ID JSON field name and format
- Exact behavior of `claude --resume` with stale/invalid session IDs

---
*Research completed: 2026-04-06*
*Ready for roadmap: yes*
