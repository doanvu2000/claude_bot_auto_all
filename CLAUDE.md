<!-- GSD:project-start source:PROJECT.md -->
## Project

**Discord Terminal Bot**

A Discord bot that acts as a remote control interface for multiple computers. Each Discord channel maps to one machine; messages sent in a channel execute shell commands or drive Claude Code sessions on that machine. A lightweight agent process running on each computer relays commands and streams output back to Discord.

**Core Value:** From any Discord client, control any registered machine's terminal and Claude Code — without opening SSH or switching apps.

### Constraints

- **Platform**: Discord only — no Telegram in v1
- **Hosting**: Runs on user's own hardware, no VPS required
- **Auth**: Discord server/channel membership as access boundary
- **Claude**: Requires `claude` CLI available on each machine
- **OS**: Must support Windows and macOS
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Summary Decision
### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| discord.py | 2.3.x | Discord bot | Actively maintained async-first Python library. The 2.x rewrite (Rapptz, 2021) resolved the abandonment scare; v2.3 is the stable current series. Native `asyncio`, slash commands, message intents. |
| websockets | 12.x | Agent ↔ Bot transport | Pure-Python async WebSocket server/client. No Node.js dependency, minimal weight, correct semantics for NAT-traversal (agents connect OUT to bot's server). |
| asyncio | stdlib | Async event loop | Ships with Python 3.11+. Drives both the discord.py client and the WebSocket server on the same event loop — no threading needed. |
### Python Runtime
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.11 minimum, prefer 3.12 | Runtime for bot + agent | 3.11 brought significant `asyncio` performance improvements. 3.12 adds better subprocess error messages. Both ship on Windows and macOS via python.org installer. Do NOT use 3.13 in early 2025 — some C extension ecosystem lag. |
### Agent ↔ Bot Communication
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| websockets (server) | 12.x | Bot hosts WS server | The bot machine runs `websockets.serve()`. Agents connect OUT through NAT. Single persistent connection per agent. |
| websockets (client) | 12.x | Agent connects to bot | Each agent runs `websockets.connect()` with exponential backoff reconnect loop. |
| JSON message protocol | N/A | Wire format | Plain JSON envelopes: `{"type": "command", "id": "...", "payload": "..."}`. No binary framing needed at this scale. |
### Process Management (Shell Command Execution)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| asyncio.create_subprocess_exec | stdlib | Execute shell commands | Async-native subprocess. Does NOT shell-inject (unlike `shell=True`). Captures stdout/stderr cleanly. Cross-platform. |
| shlex | stdlib | Argument tokenization on Unix | Safely splits command strings into argument lists for `create_subprocess_exec`. |
| subprocess (sync fallback) | stdlib | Sync subprocess for simple cases | For non-async contexts only. Prefer the async variant. |
### Claude Code CLI Integration
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| claude CLI | latest installed | Drive Claude Code on agent machine | Invoked via subprocess. Session management via `--resume`. |
| asyncio.create_subprocess_exec | stdlib | Invoke `claude` | Same subprocess pattern as shell commands. |
- `-p "<prompt>"` — non-interactive prompt mode
- `--output-format json` — machine-readable output with session metadata
- `--resume <session-id>` — resume existing session context
- `--no-permissions-prompt` — suppress interactive prompts (needed for unattended operation)
- `--max-turns <N>` — limit agentic recursion depth (safety)
- Do not run `claude` in interactive/TTY mode — it will hang waiting for input. Always use `-p`.
- Do not try to parse conversation state yourself — rely on `--resume` and the session ID only.
- Do not persist the subprocess between messages to "keep a session open" — this creates zombie processes and is fragile. Fire-and-forget with `--resume` is the correct pattern.
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.x | `.env` file loading | Load bot token, WS port, auth secret from `.env`. Never hardcode credentials. |
| aiofiles | 23.x | Async file I/O | For async reading/writing of session state files and logs. |
| pydantic | 2.x | Message schema validation | Validate incoming WebSocket message payloads. Catches malformed messages before they reach command dispatch. Optional but recommended. |
| loguru | 0.7.x | Structured logging | Better than stdlib `logging` for a long-running process. Color output, file rotation, structured context. |
## Discord Library Decision: discord.py vs discord.js vs alternatives
### discord.py 2.x — RECOMMENDED
- Application commands (slash commands)
- Message intents (required since Discord API v10)
- Proper `asyncio` integration
- Bot+Guild+Channel object model matching the project's channel-per-machine routing
### discord.js — NOT RECOMMENDED for this project
### nextcord / py-cord — NOT RECOMMENDED
### hikari — NOT RECOMMENDED
## Language Decision: Python vs Node.js
| Factor | Python | Node.js |
|--------|--------|---------|
| Discord library maturity | discord.py 2.x — stable, active | discord.js — also stable, active |
| Cross-platform subprocess | asyncio.create_subprocess_exec — excellent Windows/Mac | child_process — workable but Windows edge cases |
| Windows shell quirks | Well-documented, sys.platform branching | Similar, but cmd.exe escaping is trickier |
| Claude CLI integration | subprocess.run / asyncio — natural | child_process.spawn — works but more verbose |
| Single-file agent script | Yes — `python agent.py` | Requires node_modules or bundle |
| Deployment friction (agent) | pip install + python | npm install or bundle |
| Async model | asyncio — single event loop | EventEmitter + async/await — also fine |
| Session file management | json/pathlib — trivial | fs/path — also fine |
## What NOT to Use
| Option | Reason to Avoid |
|--------|----------------|
| `shell=True` in subprocess | Shell injection vector. Explicitly build argv lists. |
| threading for subprocess | asyncio subprocess API renders threading unnecessary and adds complexity. |
| Redis / RabbitMQ as message broker | Unnecessary infrastructure. WebSocket direct connection is sufficient. |
| ngrok as required dependency | External account requirement. Port forward or document as optional. |
| SQLite/database for session state | A JSON file on disk is sufficient. Sessions are per-channel, O(channels) count. |
| discord.py 1.x | EOL. Discord API v10 requires 2.x intent handling. |
| Python 3.10 or below | Missing `asyncio` performance work. 3.11 minimum. |
| Interactive `claude` mode (TTY) | Will hang the agent. Always use `-p` flag. |
| `asyncio.run()` inside discord.py's loop | discord.py manages its own event loop. Use `bot.loop.create_task()` or `async def setup_hook()` patterns. |
## Installation
# Bot machine (also runs the bot-side agent if desired)
# Each agent machine (minimal)
# Optional but recommended for agent machines
## Project Layout (recommended)
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Discord library | discord.py 2.3 | discord.js | Node.js not justified; subprocess story weaker |
| Discord library | discord.py 2.3 | nextcord | Fork risk; upstream restored |
| Agent transport | websockets (direct) | Redis pub/sub | Extra broker process, unjustified complexity |
| Agent transport | websockets (direct) | HTTP long-polling | Latency, TCP overhead, worse reconnect story |
| Agent transport | websockets (direct) | gRPC | Heavy; overkill for personal-scale bot |
| Session state | in-memory dict + JSON file | SQLite | Overkill; channels are bounded and small |
| CLI integration | `--resume` flag pattern | Long-running claude subprocess | Zombie process risk, harder error recovery |
| Subprocess | asyncio.create_subprocess_exec | subprocess.run (sync) | Blocks event loop on agent; async is correct |
## Open Questions (verify before implementation)
## Sources
- Training data (knowledge cutoff August 2025) — all claims
- discord.py 2.x rewrite and maintenance restoration: https://github.com/Rapptz/discord.py (MEDIUM confidence — verify current activity)
- websockets library: https://websockets.readthedocs.io/ (MEDIUM confidence — verify current version)
- Python asyncio subprocess docs: https://docs.python.org/3/library/asyncio-subprocess.html (HIGH confidence — stdlib, stable API)
- Claude Code CLI: `claude --help` on each machine (verify flags at runtime)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
