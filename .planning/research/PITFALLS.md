# Domain Pitfalls

**Domain:** Discord bot with remote terminal control + Claude Code session management
**Researched:** 2026-04-06
**Knowledge source:** Training data (cutoff August 2025). WebSearch and WebFetch were unavailable.
**Overall confidence:** HIGH for Discord API limits and subprocess behavior (stable, well-documented). MEDIUM for Claude Code CLI session behavior (newer, less stable). HIGH for security and process management fundamentals.

---

## Critical Pitfalls

Mistakes that cause rewrites, security incidents, or fundamental brokenness.

---

### Pitfall 1: No Authorization Gate on Command Execution

**Severity:** HIGH
**Affects v1:** YES — must be in initial design

**What goes wrong:**
The bot has `MESSAGE_CONTENT` intent, reads every message in a mapped channel, and executes it as a shell command on the target machine. If access control is treated as "anyone in the server can send commands" without explicit allowlisting, anyone who gets into the Discord server (via invite link, leak, social engineering) has full shell access to every registered machine.

**Why it happens:**
"Discord server membership = access" feels sufficient, but Discord invites can be compromised. There is no concept of "this user explicitly has permission to execute" baked in by default.

**Consequences:**
- Arbitrary code execution on every connected machine
- If bot host machine is connected, attacker controls the bot itself
- Lateral movement from bot host to all registered agents

**Prevention:**
- Maintain an allowlist of Discord user IDs permitted to issue commands — not just "is in server"
- Check `message.author.id` against allowlist on every command message
- Store allowlist in a config file, not hardcoded
- Consider a separate admin-only channel for managing the allowlist itself

**Detection:**
- Unexpected commands appearing in channel history
- Machine CPU/network spikes unexplained by your own activity

---

### Pitfall 2: Shell Injection via Discord Message Content

**Severity:** HIGH
**Affects v1:** YES

**What goes wrong:**
Commands arrive as raw Discord message text. If they are passed directly to `subprocess.run(cmd, shell=True)` (Python) or equivalent, an attacker can inject shell metacharacters. Example: a user types `ls; rm -rf ~` and the agent executes both parts. On Windows, `dir & del /F /Q C:\Users\...` achieves the same.

**Why it happens:**
`shell=True` is the path of least resistance for "run a terminal command". Most tutorials use it. The entire purpose of this bot is to run arbitrary commands — so the mitigation is not "sanitize the input" but "gate who can send input at all."

**Consequences:**
- Arbitrary code execution as whatever user the agent runs as
- File destruction, credential theft, data exfiltration

**Prevention:**
- For legitimate arbitrary-command use cases, `shell=True` is intentional — the mitigation is the auth layer (Pitfall 1), not input sanitization
- If you ever add restricted "safe" commands (e.g., a status ping), use `shell=False` with an explicit argument list for those paths
- Document clearly that the system is "trusted-user arbitrary shell" not "safe command sandbox"
- Never expose a command channel publicly; keep the Discord server invite-only

**Detection:**
- Shell metacharacters in command history that were not typed by you

---

### Pitfall 3: Bot Token Exposure

**Severity:** HIGH
**Affects v1:** YES — must be handled from day one

**What goes wrong:**
The Discord bot token is placed in a `.env` file or config file, that file gets committed to git, pushed to GitHub, and Discord's automated token scanner (or a bad actor) finds it. Discord will auto-invalidate tokens found in public repos, but the window between push and invalidation can be enough for abuse. For private repos, there is no scanner.

**Why it happens:**
Accidental `git add .` is the most common cause. Also: the token printed to terminal logs and captured in shell history.

**Consequences:**
- Full bot impersonation — attacker can read all channel messages the bot can see, send messages as the bot, and trigger any command the bot can run
- Since this bot executes shell commands, token compromise = shell access on all connected machines

**Prevention:**
- `.env` must be in `.gitignore` before the first `git init`
- Use `python-dotenv` or equivalent; never hardcode tokens in source
- Rotate the token immediately if any doubt about exposure
- Consider storing the token in OS keychain (macOS Keychain, Windows Credential Manager) instead of a plain file for production use
- The `agent_secret` (used to authenticate agents to the bot WebSocket) has the same exposure risk — treat it identically

**Detection:**
- Git history scan: `git log -p | grep -i token`
- GitHub secret scanning alerts (for public repos)

---

### Pitfall 4: Claude Code Session State Loss on Process Death

**Severity:** HIGH
**Affects v1:** YES — core architectural decision

**What goes wrong:**
The PROJECT.md notes "Session persistence via `claude --resume`". If the `claude` process is killed (OOM, crash, `kill` command, machine restart), the session ID stored in the agent may point to a dead or nonexistent session. The next `claude --resume <id>` either errors silently, starts a fresh session without warning, or hangs indefinitely.

The exact failure mode of `claude --resume` with a stale/invalid session ID is not well-documented and may vary between CLI versions.

**Why it happens:**
The Claude Code CLI is designed for interactive terminal use, not for programmatic invocation from a bot. Session lifecycle management is an edge case that Anthropic has not prioritized in the CLI.

**Consequences:**
- User believes they are continuing a conversation but context is gone
- Commands that assume prior context ("fix the bug we just discussed") produce wrong results
- Silent failure is worse than noisy failure here

**Prevention:**
- Wrap every `claude --resume` invocation with explicit error checking on exit code AND stdout
- If `claude --resume` fails for any reason, auto-fall-through to a new session (with notification to the user: "Session expired, starting fresh")
- Store session ID with a timestamp; treat sessions older than N hours (e.g., 8) as potentially stale
- Keep the session file on disk per-agent so a bot restart does not lose the ID

**Detection:**
- `claude --resume` returns non-zero exit code
- Stderr contains "session not found" or similar
- Response does not reference any prior context

---

### Pitfall 5: Long-Running Command Blocks the Agent

**Severity:** HIGH
**Affects v1:** YES

**What goes wrong:**
An agent spawns a subprocess for `npm install` or `git clone large-repo`. That subprocess runs for 3+ minutes. During that time, the agent is blocking on `subprocess.run()` and cannot process any new Discord messages. The Discord channel appears frozen. Another message arrives while the command runs and is silently dropped or queued with no feedback.

**Why it happens:**
`subprocess.run()` is synchronous. Using it in a synchronous command handler means one command monopolizes the agent.

**Consequences:**
- Agent becomes unresponsive mid-command
- No way to cancel a running command
- Second command from user arrives, is either dropped or queued indefinitely
- Bot host can also be affected if bot itself is synchronous

**Prevention:**
- Use `asyncio.create_subprocess_exec` (Python async subprocess) — non-blocking
- Immediately ACK the command back to Discord ("Running: `npm install`...") before starting the subprocess
- Stream stdout/stderr lines back to Discord as they arrive (or periodically, to avoid rate limits)
- Implement a timeout per command (configurable; default 5 minutes)
- Implement a `/cancel` command that sends SIGTERM/SIGKILL to the running subprocess PID

**Detection:**
- Agent stops responding to test pings while a command is running

---

## Moderate Pitfalls

---

### Pitfall 6: Discord Message Length Limit (2000 characters)

**Severity:** MEDIUM
**Affects v1:** YES — must handle in v1 output routing

**What goes wrong:**
Command output (especially `ls -la`, `git log`, compiler errors, `pip install` output) routinely exceeds 2000 characters. Attempting to send a message longer than 2000 characters via the Discord API returns a 400 error. If the bot does not handle this, the output is silently lost.

**Why it happens:**
Discord's hard limit on message content is 2000 characters. This is a published API constraint, not an edge case.

**Consequences:**
- Truncated output with no indication that truncation occurred
- If the bot crashes on the 400 error rather than truncating gracefully, the user gets nothing

**Prevention:**
- Chunk all output into ≤1990-character segments (leave margin for formatting like code blocks)
- Send chunks as sequential messages or as a Discord file attachment (no size limit for files under 8MB on free servers, 25MB on Nitro)
- For very large output (>10KB), prefer file attachment over many messages
- Always wrap command output in code blocks (```\n...\n```) — this consumes 8 characters of the budget
- Project.md notes "full output reply for v1" — this is fine, but truncation handling must be explicit

**Detection:**
- `discord.HTTPException` with status 400 and "Must be 2000 or fewer in length"

---

### Pitfall 7: Discord Rate Limits

**Severity:** MEDIUM
**Affects v1:** YES — streaming/chunked output is the trigger

**What goes wrong:**
The global rate limit for bots is 50 requests per second. Per-channel send-message rate limit is more restrictive in practice: approximately 5 messages per 5 seconds per channel before Discord starts returning 429 responses. If a command produces many output chunks and the bot sends them rapidly, it hits rate limits. Unhandled 429s lose messages.

**Why it happens:**
Streaming command output line-by-line to Discord violates rate limits almost immediately for verbose commands.

**Consequences:**
- 429 responses cause message loss if not retried
- Discord may temporarily ban the bot if rate limit violations are persistent
- `discord.py` handles 429 rate limits automatically by sleeping and retrying — but this means the agent's send queue backs up, adding latency

**Prevention:**
- Do not send output line-by-line; buffer and send in chunks of ≤1990 chars
- `discord.py`'s built-in rate limit handling is generally sufficient for moderate use — do not disable it
- For high-volume output, prefer a single file attachment over 20 small messages
- Add a minimum inter-message delay (100-200ms) for sequential output chunks

**Detection:**
- `discord.py` logs will show 429 warnings with retry-after headers

---

### Pitfall 8: Zombie and Orphan Processes

**Severity:** MEDIUM
**Affects v1:** YES

**What goes wrong:**
A command is started via subprocess. The command spawns child processes (e.g., `npm install` spawns node, which spawns compilers). If the parent subprocess is killed (via timeout or `/cancel`), the children may continue running as orphans. On Linux/macOS this is common; on Windows the behavior differs.

Additionally, if the agent crashes and restarts, any subprocesses it was tracking are now orphans with no owner.

**Why it happens:**
Python's `subprocess.kill()` sends SIGTERM/SIGKILL to the direct child only, not the entire process tree. Windows `TerminateProcess` only kills the named process.

**Consequences:**
- Runaway `node`, `python`, or `claude` processes consuming CPU/RAM
- Multiple `claude` processes potentially conflicting over the same session file
- Machine slowdown or OOM

**Prevention:**
- Use `os.killpg` (Unix) to kill the entire process group: `os.killpg(os.getpgid(proc.pid), signal.SIGTERM)`
- On Windows, use `subprocess.Popen` with `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` and `proc.send_signal(signal.CTRL_BREAK_EVENT)` — or use `taskkill /F /T /PID <pid>` for tree kill
- Keep a registry of active subprocess PIDs on the agent; on startup, check for and kill orphaned PIDs from a previous session
- Wrap all subprocess invocations in a context manager or try/finally that ensures cleanup

**Detection:**
- `ps aux | grep claude` or `tasklist | findstr claude` showing multiple instances
- Agent startup finds a stale PID file

---

### Pitfall 9: WebSocket Reconnection Storms

**Severity:** MEDIUM
**Affects v1:** YES — agent reconnect logic is in scope

**What goes wrong:**
The bot's WebSocket server restarts (or the network blips). All N agents attempt to reconnect simultaneously. If each agent retries immediately with no backoff, they generate a thundering herd that can overwhelm the bot's connection handler and itself get rate-limited by the OS (too many simultaneous TCP connections).

**Why it happens:**
Naive reconnect: `while not connected: connect(); sleep(1)`. All agents use the same 1-second interval.

**Consequences:**
- Bot spends all its time refusing/accepting connections rather than processing commands
- Some agents fail to reconnect and stay offline indefinitely
- If the bot is also a Discord bot, the rapid reconnects may log noisy errors

**Prevention:**
- Implement exponential backoff with jitter on every reconnect path: `wait = min(base * 2^attempt + random(0, 1), max_wait)`
- Base: 1s, Max: 60s, Jitter: ±0-5s
- Apply this to both: (a) agent → bot WebSocket reconnect, (b) bot → Discord gateway reconnect
- `discord.py` handles Discord gateway reconnect with backoff automatically — do not override it

**Detection:**
- Log spam of "Connection refused" or "Connection reset" on agent side
- Bot log showing many new connections per second on startup

---

### Pitfall 10: Windows vs. macOS Shell Differences

**Severity:** MEDIUM
**Affects v1:** YES — cross-platform support is a core requirement

**What goes wrong:**
Commands that work on macOS bash/zsh fail silently or error on Windows cmd/PowerShell:
- `ls` is not a native Windows cmd command (it works in PowerShell but not cmd)
- Path separators: `~/Documents` expands on macOS, not on cmd
- Line endings: subprocess output on Windows uses `\r\n`; naively sending to Discord shows garbage or double-newlines
- Environment variable syntax: `$HOME` (Unix) vs `%USERPROFILE%` (cmd) vs `$env:USERPROFILE` (PowerShell)
- `grep`, `cat`, `which`, `ps` are absent in native Windows cmd
- `subprocess.run("cmd_string", shell=True)` uses `cmd.exe` on Windows, `/bin/sh` on Unix — entirely different interpreters

**Why it happens:**
Shell commands are not portable. The bot routes arbitrary shell commands typed by the user, but what "shell" means differs by OS.

**Consequences:**
- Commands that work on your Mac fail on your Windows machine and vice versa
- Users must mentally track which machine they're targeting and which shell it uses

**Prevention:**
- The agent must report its platform and default shell in its registration message so the user knows what shell they're typing for
- Do not attempt to normalize/translate shell syntax — it is an unsolvable general problem
- For Windows, default to PowerShell (not cmd) since PowerShell supports `ls`, `cat`, `grep` aliases
- Use `sys.platform` on the agent to detect OS and invoke the correct shell: `powershell.exe -Command ...` on Windows, `/bin/bash -c ...` on macOS
- Decode subprocess stdout with `errors='replace'` to handle encoding differences (Windows often uses CP1252/CP850, not UTF-8)

**Detection:**
- Windows subprocess output containing `\r\n` double-spaced in Discord
- UnicodeDecodeError in agent logs

---

### Pitfall 11: Message Ordering Not Guaranteed

**Severity:** MEDIUM
**Affects v1:** PARTIAL — matters if chunking output across multiple messages

**What goes wrong:**
If the bot sends multiple sequential messages rapidly (chunked output), Discord does not guarantee delivery order. A user may see chunk 3 before chunk 2. This makes large outputs confusing.

**Why it happens:**
Discord's CDN and message delivery is eventually consistent. Rapid sequential API calls do not guarantee FIFO ordering in the channel view under load.

**Consequences:**
- Multi-chunk command output appears scrambled
- Difficult to diagnose: works fine locally, fails intermittently under load

**Prevention:**
- `await` each `channel.send()` before sending the next chunk — do not fire-and-forget multiple sends
- Number the chunks: `[1/3] output...`, `[2/3] output...` so the user can reorder mentally if needed
- For large outputs, prefer a single file attachment over multiple messages (one API call, ordering is trivial)

**Detection:**
- Testing with a 10KB output that produces 5+ chunks

---

### Pitfall 12: Privileged Intents Not Requested

**Severity:** MEDIUM
**Affects v1:** YES — bot will not function without correct intents

**What goes wrong:**
Since Discord's April 2022 "message content intent" change, bots must explicitly request the `MESSAGE_CONTENT` privileged intent to read the text of messages in channels (other than DMs and messages that @mention the bot). Without it, `message.content` is an empty string. The bot appears to work (no error), but all commands are invisible to it.

**Why it happens:**
This is a "privileged intent" — it must be enabled both in the Discord Developer Portal AND declared in the bot's code. Forgetting either silently breaks the bot.

**Consequences:**
- Bot receives message events but sees empty content
- All commands are silently ignored
- Extremely confusing to debug — no exception is raised

**Prevention:**
- In Discord Developer Portal: Bot → Privileged Gateway Intents → enable "Message Content Intent"
- In code: `intents = discord.Intents.default(); intents.message_content = True`
- Also enable "Server Members Intent" if you need to check server membership for auth
- Document these steps in the README as a hard prerequisite — this is a common first-time setup failure

**Required permissions for this bot:**
- `Read Messages / View Channels` — see channels
- `Send Messages` — send output back
- `Attach Files` — for large output file attachments
- `Read Message History` — needed for some slash command contexts
- `Use Application Commands` — for slash commands

**Detection:**
- Bot is online, receives events, but `message.content` is always `""`

---

## Minor Pitfalls

---

### Pitfall 13: Slash Commands vs. Prefix Commands Registration Delay

**Severity:** LOW
**Affects v1:** LOW — design choice, not a failure mode

**What goes wrong:**
Discord slash commands (application commands) registered globally take up to 1 hour to propagate. Guild-scoped commands are instant. During development, global command registration causes a frustrating "command not appearing for an hour" cycle.

**Prevention:**
- Register slash commands as guild-scoped commands during development (pass `guild=` to `@tree.command`)
- Switch to global registration only for "production" deployment
- For this project's use case (small group, own server), guild-scoped commands may be preferable permanently

---

### Pitfall 14: Agent Registers with Wrong Channel Mapping

**Severity:** LOW
**Affects v1:** LOW — initialization error, not runtime

**What goes wrong:**
An agent registers itself by machine name, but the bot maps machine names to channels via config. If the config has a typo or the channel was renamed, commands go to the wrong machine (or nowhere).

**Prevention:**
- On agent registration, have the bot echo back the resolved channel name so the user can verify mapping immediately
- Validate channel IDs exist at bot startup, not lazily at first use

---

### Pitfall 15: Claude Code CLI Output Format Changes

**Severity:** LOW (now) — could become MEDIUM if CLI changes frequently
**Affects v1:** MEDIUM — output parsing is core to the feature

**What goes wrong:**
`claude -p "prompt" --resume session_id` is invoked via subprocess. The bot parses stdout to extract the response text. If Anthropic changes the output format, JSON envelope structure, or adds progress indicators to stdout, the parser breaks silently.

**Why it happens:**
The Claude Code CLI (`claude`) is a relatively new tool primarily designed for interactive use, not programmatic subprocess invocation. Its stdout contract is less stable than a dedicated API.

**Consequences:**
- `claude` commands appear to succeed (exit 0) but the bot returns garbage or empty strings to Discord

**Prevention:**
- Use `--output-format json` or equivalent flag if available — structured output is more stable than human-readable text
- Pin the `claude` CLI version per machine (note version in setup docs)
- Add an integration test: run a known prompt, assert the response contains expected text, to detect breakage early
- Check Anthropic release notes when upgrading `claude` CLI version

**Confidence note:** LOW confidence on exact `--output-format` flag availability — verify against current `claude --help` output.

---

### Pitfall 16: Discord Gateway Heartbeat Miss Causes Reconnect

**Severity:** LOW
**Affects v1:** LOW — `discord.py` handles this automatically

**What goes wrong:**
The Discord Gateway requires bots to send a heartbeat (PING) at a defined interval (typically 41.25 seconds, varying per session). If the bot's event loop is blocked (e.g., by a synchronous subprocess call), it misses a heartbeat, Discord closes the connection with opcode 1001, and the bot must fully reconnect and potentially re-identify.

**Why it happens:**
Any synchronous blocking in the `discord.py` event loop delays heartbeats.

**Consequences:**
- Bot briefly goes offline and misses messages during reconnect (~1-5 seconds)
- Repeated heartbeat misses look like bot instability

**Prevention:**
- Never call `subprocess.run()` (blocking) in a `discord.py` async event handler
- Always use `asyncio.create_subprocess_exec` or `loop.run_in_executor` for subprocess work
- This is the same fix as Pitfall 5 — async subprocess kills two pitfalls at once

---

### Pitfall 17: Windows Encoding Issues in Subprocess Output

**Severity:** LOW
**Affects v1:** MEDIUM for Windows agents

**What goes wrong:**
Windows subprocesses (cmd.exe, PowerShell) default to the system code page (often CP850 or CP1252), not UTF-8. Python's subprocess will raise `UnicodeDecodeError` when decoding output that contains extended characters (accented letters, box-drawing characters from some CLI tools).

**Prevention:**
- `subprocess.run(..., encoding='utf-8', errors='replace')` — replace undecodable bytes with `?`
- For PowerShell: `powershell.exe -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; ..."` forces UTF-8 output
- On Windows Python 3.7+, set `PYTHONUTF8=1` environment variable to make the Python process itself UTF-8 by default

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation | Affects v1? |
|-------------|---------------|------------|-------------|
| Bot setup / auth | Missing `MESSAGE_CONTENT` privileged intent | Enable in portal AND code before any testing | YES |
| Bot setup / auth | Bot token in `.env` committed to git | `.gitignore` the `.env` before first commit | YES |
| Command routing | Authorization gate absent | Allowlist user IDs; don't rely on server membership alone | YES |
| Command execution | `shell=True` + no auth = RCE | Auth layer IS the mitigation; document this explicitly | YES |
| Command execution | Synchronous subprocess blocks event loop | Use `asyncio.create_subprocess_exec` throughout | YES |
| Output handling | Output >2000 chars truncated silently | Chunk or attach as file; wrap in code block | YES |
| Output handling | Rapid chunk sends hit rate limits | `await` each send; add inter-message delay | YES |
| Agent WebSocket | Reconnect storm on restart | Exponential backoff with jitter | YES |
| Claude Code sessions | Session ID stale after CLI/machine restart | Validate `--resume` success; fall through to new session | YES |
| Claude Code sessions | CLI stdout format changes break parser | Use `--output-format json` if available; pin CLI version | YES |
| Long-running commands | Agent frozen for duration of command | Async subprocess; ACK immediately; timeout + cancel | YES |
| Process cleanup | Orphan processes after crash/cancel | Kill entire process group, not just parent PID | YES |
| Cross-platform | Shell behavior differs Windows vs macOS | Report platform on agent registration; use platform-correct shell | YES |
| Windows agents | Encoding errors in subprocess output | `errors='replace'` in decode; force UTF-8 in PowerShell | YES |
| Slash commands | Global commands take 1h to propagate | Use guild-scoped commands during development | LOW |

---

## Sources

**Confidence note:** WebSearch and WebFetch were unavailable during this research session. All findings are based on training data (cutoff August 2025). The following claims are well-established and unlikely to have changed:
- Discord 2000-character message limit (has been this value for years)
- `MESSAGE_CONTENT` privileged intent requirement (introduced April 2022, stable since)
- `discord.py` automatic rate limit handling behavior
- Python subprocess process group kill behavior (`os.killpg`)
- Exponential backoff as standard reconnect strategy

The following claims have lower confidence and should be verified at implementation time:
- `claude --output-format json` flag existence and exact syntax — check `claude --help`
- Exact behavior of `claude --resume` with an invalid/expired session ID — test manually
- Discord gateway heartbeat interval (currently ~41.25s but session-specific — `discord.py` manages this automatically)

**Reference URLs (to verify at implementation time):**
- Discord Developer Docs — Rate Limits: https://discord.com/developers/docs/topics/rate-limits
- Discord Developer Docs — Gateway Intents: https://discord.com/developers/docs/topics/gateway#gateway-intents
- discord.py docs: https://discordpy.readthedocs.io/en/stable/
- Anthropic Claude Code CLI docs: https://docs.anthropic.com/en/docs/claude-code
