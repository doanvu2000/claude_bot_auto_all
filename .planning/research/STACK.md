# Technology Stack

**Project:** Discord Terminal Bot  
**Researched:** 2026-04-06  
**Note on sources:** WebSearch, WebFetch, and Bash tools were unavailable during this research session. All findings are drawn from training data (knowledge cutoff August 2025). Confidence levels reflect this constraint — all HIGH/MEDIUM claims should be spot-checked against current PyPI/npm before implementation begins.

---

## Recommended Stack

### Summary Decision

**Use Python throughout.** The bot, the agent, and the CLI integration layer are all Python. Node.js is not a better fit here — the advantages of discord.js are irrelevant when the dominant workload is subprocess management, cross-platform shell execution, and a persistent WebSocket server. Python's `asyncio` + `subprocess` story is mature and well-documented for exactly this use case.

---

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| discord.py | 2.3.x | Discord bot | Actively maintained async-first Python library. The 2.x rewrite (Rapptz, 2021) resolved the abandonment scare; v2.3 is the stable current series. Native `asyncio`, slash commands, message intents. |
| websockets | 12.x | Agent ↔ Bot transport | Pure-Python async WebSocket server/client. No Node.js dependency, minimal weight, correct semantics for NAT-traversal (agents connect OUT to bot's server). |
| asyncio | stdlib | Async event loop | Ships with Python 3.11+. Drives both the discord.py client and the WebSocket server on the same event loop — no threading needed. |

**Confidence:** MEDIUM. discord.py 2.3 and websockets 12.x were accurate as of mid-2025. Verify exact latest patch versions on PyPI before pinning in requirements.txt.

---

### Python Runtime

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.11 minimum, prefer 3.12 | Runtime for bot + agent | 3.11 brought significant `asyncio` performance improvements. 3.12 adds better subprocess error messages. Both ship on Windows and macOS via python.org installer. Do NOT use 3.13 in early 2025 — some C extension ecosystem lag. |

**Confidence:** HIGH. Python 3.11/3.12 stability is well-established.

---

### Agent ↔ Bot Communication

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| websockets (server) | 12.x | Bot hosts WS server | The bot machine runs `websockets.serve()`. Agents connect OUT through NAT. Single persistent connection per agent. |
| websockets (client) | 12.x | Agent connects to bot | Each agent runs `websockets.connect()` with exponential backoff reconnect loop. |
| JSON message protocol | N/A | Wire format | Plain JSON envelopes: `{"type": "command", "id": "...", "payload": "..."}`. No binary framing needed at this scale. |

**Why not HTTP polling:** Polling adds 1-30s latency per cycle. For a terminal bot, this makes the UX feel broken. WebSocket gives sub-100ms round-trips with no extra infrastructure.

**Why not Redis pub/sub:** Redis requires running a third process (the broker). For a personal bot connecting a handful of machines, that overhead is unjustified. WebSocket is peer-to-peer enough.

**Why not SSE (Server-Sent Events):** SSE is one-directional (server → client). Agents need bidirectional communication.

**Why not ngrok / reverse tunnel:** ngrok works but introduces an external dependency and requires account management. Since the bot runs on the user's own machine, just expose a port. If the machine is behind NAT, document that port forwarding is needed — or add optional ngrok support as a later enhancement.

**Confidence:** HIGH. The WebSocket + JSON pattern for this topology is well-understood and has no meaningful alternatives at this scale.

---

### Process Management (Shell Command Execution)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| asyncio.create_subprocess_exec | stdlib | Execute shell commands | Async-native subprocess. Does NOT shell-inject (unlike `shell=True`). Captures stdout/stderr cleanly. Cross-platform. |
| shlex | stdlib | Argument tokenization on Unix | Safely splits command strings into argument lists for `create_subprocess_exec`. |
| subprocess (sync fallback) | stdlib | Sync subprocess for simple cases | For non-async contexts only. Prefer the async variant. |

**Critical cross-platform notes:**

On Windows, use `asyncio.create_subprocess_exec("cmd.exe", "/c", command)` or `("powershell.exe", "-Command", command)`. On macOS/Linux, use `("/bin/bash", "-c", command)` or `("/bin/zsh", "-c", command)`.

Do NOT use `shell=True` in production — it is a shell injection vector. Build the shell invocation explicitly per OS.

Use `sys.platform` to branch:
```python
import sys
if sys.platform == "win32":
    shell_args = ["cmd.exe", "/c", command]
else:
    shell_args = ["/bin/bash", "-c", command]
```

**Output size management:** Discord messages cap at 2000 characters. Truncate or chunk subprocess output before sending. A utility that splits at 1900 chars with `` ```\n ``` `` fences is necessary.

**Timeout enforcement:** Always pass `timeout=` to subprocess calls. Default 30s for commands, configurable per command type. Without this, a hung command blocks the agent.

**Confidence:** HIGH. asyncio subprocess API is stable and well-documented.

---

### Claude Code CLI Integration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| claude CLI | latest installed | Drive Claude Code on agent machine | Invoked via subprocess. Session management via `--resume`. |
| asyncio.create_subprocess_exec | stdlib | Invoke `claude` | Same subprocess pattern as shell commands. |

**Session management strategy:**

The `claude` CLI (as of 2025) supports session persistence through the `--resume <session-id>` flag. The session ID is printed in JSON output when using `claude --output-format json`.

Recommended flow:
1. First message in a channel: run `claude -p "<prompt>" --output-format json`
2. Parse the `session_id` field from JSON output
3. Store `session_id` mapped to the Discord channel ID in a JSON file on disk (or in-memory dict)
4. Subsequent messages: run `claude -p "<prompt>" --resume <session_id> --output-format json`
5. On `/new-session`: clear the stored session ID for that channel

**Flag reference (confidence MEDIUM — verify against `claude --help` on each machine):**
- `-p "<prompt>"` — non-interactive prompt mode
- `--output-format json` — machine-readable output with session metadata
- `--resume <session-id>` — resume existing session context
- `--no-permissions-prompt` — suppress interactive prompts (needed for unattended operation)
- `--max-turns <N>` — limit agentic recursion depth (safety)

**What NOT to do:**
- Do not run `claude` in interactive/TTY mode — it will hang waiting for input. Always use `-p`.
- Do not try to parse conversation state yourself — rely on `--resume` and the session ID only.
- Do not persist the subprocess between messages to "keep a session open" — this creates zombie processes and is fragile. Fire-and-forget with `--resume` is the correct pattern.

**Confidence:** MEDIUM. The `--resume` flag and JSON output format were present in Claude Code CLI as of mid-2025, but CLI flags can change between versions. Run `claude --help` on each agent machine at startup and log the available flags.

---

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.x | `.env` file loading | Load bot token, WS port, auth secret from `.env`. Never hardcode credentials. |
| aiofiles | 23.x | Async file I/O | For async reading/writing of session state files and logs. |
| pydantic | 2.x | Message schema validation | Validate incoming WebSocket message payloads. Catches malformed messages before they reach command dispatch. Optional but recommended. |
| loguru | 0.7.x | Structured logging | Better than stdlib `logging` for a long-running process. Color output, file rotation, structured context. |

**Confidence:** MEDIUM. All four libraries are stable, mature projects with consistent APIs since 2022.

---

## Discord Library Decision: discord.py vs discord.js vs alternatives

### discord.py 2.x — RECOMMENDED

**Why:** Python throughout the codebase is the overriding constraint. discord.py 2.x is actively maintained by Rapptz (the original author who returned after the 2021 abandonment period). The 2.x async rewrite is production-quality. It supports:
- Application commands (slash commands)
- Message intents (required since Discord API v10)
- Proper `asyncio` integration
- Bot+Guild+Channel object model matching the project's channel-per-machine routing

**Current state (as of mid-2025):** v2.3.x. PyPI page: https://pypi.org/project/discord.py/

### discord.js — NOT RECOMMENDED for this project

**Why not:** Switching to Node.js buys nothing. discord.js is excellent and arguably has better Discord feature coverage, but the agent side (subprocess, process management, cross-platform shell) is significantly more awkward in JavaScript. `child_process` in Node.js works, but Python's `asyncio.create_subprocess_exec` has better Windows support and the ecosystem around cross-platform shell execution is more mature in Python.

If the project were purely a Discord interaction bot with no shell execution, discord.js would be equally valid.

### nextcord / py-cord — NOT RECOMMENDED

**Why not:** Both are forks of discord.py that diverged during the v1 maintenance gap. Now that discord.py 2.x is actively maintained again, prefer the upstream. Using a fork adds risk of falling behind Discord API updates without the original maintainer's attention.

### hikari — NOT RECOMMENDED

**Why not:** hikari is a well-designed async Python Discord library, but it has a steeper learning curve and a smaller community than discord.py. No advantage for this project.

---

## Language Decision: Python vs Node.js

**Use Python.** Here is the reasoning:

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

The agent script must be installable on any machine with minimum friction. `pip install discord-terminal-agent` (or even just `pip install websockets` + copy one file) is simpler than an npm package.

---

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

---

## Installation

```bash
# Bot machine (also runs the bot-side agent if desired)
pip install "discord.py>=2.3" websockets aiofiles python-dotenv loguru

# Each agent machine (minimal)
pip install websockets

# Optional but recommended for agent machines
pip install aiofiles loguru
```

---

## Project Layout (recommended)

```
bot_auto_all/
  bot/
    __init__.py
    main.py           # discord.py Client, channel routing table
    ws_server.py      # websockets server, agent registry
    command_router.py # dispatch Discord messages to correct agent
    output_formatter.py # chunk/truncate output for Discord 2000-char limit
  agent/
    agent.py          # single-file agent: WS client + subprocess runner
    claude_runner.py  # claude CLI integration, session ID management
    shell_runner.py   # cross-platform subprocess wrapper
  shared/
    protocol.py       # JSON message schema (shared between bot and agent)
  .env                # BOT_TOKEN, WS_PORT, WS_SECRET
  requirements.txt
  requirements-agent.txt  # minimal deps for agent machines
```

---

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

---

## Open Questions (verify before implementation)

1. **`claude --resume` flag name** — Confirm the exact flag on each target machine with `claude --help`. The flag may be `--resume`, `--continue`, or `--session`. MEDIUM confidence on the exact name.

2. **`--output-format json` session ID field name** — The JSON key for the session ID in claude CLI output needs to be confirmed by running a test invocation and inspecting output. Look for keys like `session_id`, `sessionId`, or similar.

3. **discord.py 2.3 vs 2.4** — Check PyPI for whether 2.4 has shipped. Pin to the latest stable 2.x. https://pypi.org/project/discord.py/#history

4. **websockets v12 vs v13** — The websockets library releases frequently. v12 was stable mid-2025; check for v13. The API changed significantly at v10→v11, so pin the minor version. https://pypi.org/project/websockets/#history

5. **Windows asyncio subprocess on Python 3.12** — Windows uses ProactorEventLoop for subprocess support. Python 3.8+ defaults to ProactorEventLoop on Windows, so this should be automatic. Verify in a Windows test environment early.

6. **Port exposure for WebSocket server** — The bot machine needs a port open (default: 8765 or similar) for agents to connect. If the bot machine is behind NAT/firewall, document the port forwarding requirement. This is an ops constraint, not a code constraint.

---

## Sources

- Training data (knowledge cutoff August 2025) — all claims
- discord.py 2.x rewrite and maintenance restoration: https://github.com/Rapptz/discord.py (MEDIUM confidence — verify current activity)
- websockets library: https://websockets.readthedocs.io/ (MEDIUM confidence — verify current version)
- Python asyncio subprocess docs: https://docs.python.org/3/library/asyncio-subprocess.html (HIGH confidence — stdlib, stable API)
- Claude Code CLI: `claude --help` on each machine (verify flags at runtime)
