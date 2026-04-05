# Feature Landscape

**Domain:** Discord bot — remote terminal + AI session control
**Researched:** 2026-04-06
**Confidence note:** External search tools unavailable. All findings from training data (knowledge cutoff August 2025) covering Discord/Telegram terminal bots, IRC shellbots, and remote control bot ecosystems. Confidence levels reflect training-data certainty only.

---

## Table Stakes

Features users expect from any remote terminal bot. Missing one of these = product feels broken or untrustworthy.

| Feature | Why Expected | Complexity | Confidence | Notes |
|---------|--------------|------------|------------|-------|
| Execute arbitrary shell commands | Core promise — it's a terminal bot | Low | HIGH | Must handle both Windows (cmd/PowerShell) and macOS (bash/zsh) |
| Return command output to Discord | Without this, commands are fire-and-forget | Low | HIGH | Must truncate intelligently — Discord message cap is 2000 chars |
| Output truncation + overflow handling | Commands like `ls -R` or `cat largefile` produce huge output | Low | HIGH | Truncate at limit, note that output was cut; never silently drop |
| Exit code / error signal | Users need to know if a command failed | Low | HIGH | Show non-zero exit codes; stderr vs stdout distinction is a plus |
| Working directory persistence per session | `cd` should stick across messages | Medium | HIGH | No persistence = every command starts at home dir, extremely confusing |
| Authorized-user-only execution | The moment this bot is in a server, security is table stakes | Low | HIGH | Discord user ID allowlist; channel-level access is not sufficient alone |
| Machine online/offline status | Users must know if a machine is unreachable before sending commands | Low | HIGH | Status message or reaction when agent connects/disconnects |
| Command timeout + kill | Long-running commands must not hang the bot forever | Medium | HIGH | Configurable timeout; forced kill with notification |
| Error messages that explain failure | "Command failed" is not enough — which machine, which command, what error | Low | HIGH | Include machine name, original command, stderr snippet |
| `/help` or command listing | Users forget syntax; discovery is essential | Low | HIGH | Slash commands help here; list available bot commands |

---

## Differentiators

Features that set a good terminal bot apart from a basic one. Not universally expected, but meaningfully raise quality.

| Feature | Value Proposition | Complexity | Confidence | Notes |
|---------|-------------------|------------|------------|-------|
| Claude Code session management | The entire AI-session capability is a differentiator vs pure terminal bots | Medium | HIGH | `/new-session` to reset; session ID persistence across messages is what makes it conversational |
| Code block formatting for output | Shell output in a Discord code block (` ``` `) is dramatically more readable | Low | HIGH | Auto-detect language if possible; always use monospace at minimum |
| Machine heartbeat + reconnect | Agents that silently drop and auto-reconnect without user action | Medium | HIGH | Users shouldn't have to restart agents manually |
| Output chunking for long responses | Split output across multiple Discord messages cleanly | Low | MEDIUM | Better than hard truncation — shows all output, paginated |
| Command history per channel | Recall last N commands; `/history` or scrolling context | Medium | MEDIUM | Quality-of-life; reduces retyping |
| Stdin / interactive command support | Send input to a running process (e.g., answer a prompt mid-command) | High | MEDIUM | Needed for `pip install` confirmations, interactive scripts — significant complexity |
| `ctrl+c` / process kill command | Kill a running command mid-execution | Medium | HIGH | Essential when a command hangs; `/kill` or a reaction trigger |
| Per-machine environment variables | Set env vars that persist across commands on a given agent | Medium | LOW | Useful for PATH, secrets injection — adds significant state management |
| Multi-line command blocks | Paste a bash script block and run it atomically | Low | HIGH | Discord code blocks as input; run as a script file, not line-by-line |
| Output file upload for large results | When output exceeds Discord limits, upload as `.txt` attachment | Low | HIGH | Much better UX than truncation for large outputs like test runs |
| Session context summary | "You are currently in Claude session X, last message was Y ago" | Low | MEDIUM | Reduces disorientation after returning to a session |
| Startup command per machine | Run a set of commands when an agent comes online | Medium | LOW | Useful for environment setup — cd to project dir, activate venv, etc. |
| Command aliases | Define `/run-tests` as shorthand for `npm test && npm run lint` | Medium | LOW | Power-user feature; reduces repetitive typing |

---

## Anti-Features

Things that make terminal bots annoying, dangerous, or abandonware. Explicitly avoid these.

| Anti-Feature | Why Avoid | What to Do Instead | Confidence |
|--------------|-----------|-------------------|------------|
| Silent output truncation | User thinks command succeeded but output was cut — data loss illusion | Always indicate truncation explicitly: "Output truncated at 1800 chars — 4200 chars omitted" | HIGH |
| Blocking the bot on long commands | If one machine runs `sleep 600`, no other channel can respond | Run each command in a subprocess/thread; bot must remain responsive | HIGH |
| Global command execution (no authorization) | Any server member can run arbitrary shell commands on your machine | Enforce an allowlist of Discord user IDs checked before any execution | HIGH |
| Echoing commands that contain secrets | User pastes `export API_KEY=xyz123`, bot echoes it in channel | Never echo raw command content; acknowledge receipt without repeating it | MEDIUM |
| Indistinguishable bot output from user messages | Users can't tell what the bot said vs what they typed | All bot output uses a consistent format: machine name header, code block body | HIGH |
| Storing command history in Discord indefinitely | Command history in a channel can reveal secrets, file paths, system state | This is inherent to Discord channels — document it; don't log sensitive commands additionally |  MEDIUM |
| Slash commands for everything | Slash commands have a 100-command limit and require interaction tokens (3-second reply deadline) | Use slash commands for control actions; use plain messages for shell input | HIGH |
| Treating newlines in Discord messages as separate commands | Mobile Discord users frequently send multi-line messages | Define a clear delimiter; default to whole-message = one command | HIGH |
| No feedback for command receipt | User sends a command, bot is silent for 30s while it runs — did it receive it? | Acknowledge receipt immediately (reaction or brief reply) before output arrives | HIGH |
| Killing the session on bot restart | If the bot restarts, all Claude session IDs are lost | Persist session IDs to disk; restore on reconnect | MEDIUM |
| One-size-fits-all timeout | `ls` and `npm install` need very different timeouts | Configurable timeout; sensible default (30s); let users override per-command | MEDIUM |
| Auto-join any Discord server | A bot that joins any server is a security surface | Require explicit server whitelisting; reject guild join events for unknown servers | HIGH |

---

## Feature Dependencies

```
Shell execution
  → Working directory persistence (cd must be stateful)
  → Command timeout + kill (execution must be interruptible)
  → Output handling (truncation, code blocks, chunking)
      → Output file upload (fallback when chunking is insufficient)

Authorization check
  → Every execution path (shell, Claude session, control commands)

Agent connection
  → Machine status reporting (online/offline)
  → Heartbeat + auto-reconnect

Claude Code session
  → Session ID persistence (disk, not memory)
  → /new-session reset
  → Session context summary (optional, differentiator)

Multi-line command support
  → Script block execution (natural extension)
```

---

## UX Patterns — Command Syntax

Based on patterns established by Telegram terminal bots, IRC shellbots, and Discord utility bots:

### Shell Command Input (table stakes pattern)

Plain message in channel = shell command. No prefix required. This is the mental model when a channel IS the machine.

```
# User types in #machine-desktop:
ls -la ~/projects

# Bot replies:
[machine-desktop] $ ls -la ~/projects
```
drwxr-xr-x  12 user staff  384 Apr 06 09:12 .
drwxr-xr-x  45 user staff 1440 Apr 05 18:00 ..
drwxr-xr-x   8 user staff  256 Apr 06 09:10 bot_auto_all
...
```
Exit: 0
```

Rationale: Prefix-free input is the most natural model when a channel maps 1:1 to a machine. Every message is a command. This matches the mental model of "this channel IS the terminal."

### Control Commands (slash or prefix)

Bot control actions (not shell commands) use slash commands or a reserved prefix:

```
/new-session          — Reset Claude Code session
/kill                 — Kill the currently running command
/status               — Show machine connection status
/history              — Show last N commands
/help                 — List available commands
```

Rationale: Slash commands visually distinguish "talking to the bot" from "talking to the machine." They also get autocomplete in Discord.

### Claude Code Session Input

Same channel, same plain-message input — context determines whether it routes to Claude. A mode toggle or a per-message prefix could work:

```
Option A (mode toggle):
  /claude              — enter Claude mode; all messages go to claude session
  /shell               — return to shell mode

Option B (per-message prefix):
  > Tell me what files are in this directory  — routes to Claude
  (plain message)                             — routes to shell
```

Option A is simpler UX. Option B is more flexible. Decision should be made during implementation — flag for roadmap.

### Output Formatting (table stakes pattern)

```
[machine-name] Command output:
```language
[stdout content]
```
Exit: [code] | Time: [duration]ms
[stderr: [content]] (only if non-empty)
```

For truncated output:
```
[machine-name] Output truncated (showing 1800/6240 chars):
```
[first 1800 chars]
```
Full output attached: output.txt
```

---

## Long-Running Command Patterns

Based on Telegram terminal bot ecosystems and Discord bot patterns:

### Pattern 1: Acknowledge-then-reply (table stakes)
1. Bot sends "Running..." or reacts with a clock emoji immediately on receipt
2. Command runs in background subprocess
3. Bot edits the message or sends a new reply when complete

Limitation: Discord does not allow editing messages after 15 minutes (interaction token). For very long commands, a new message is safer.

**Confidence: HIGH** — this is the universal pattern across all chat-based terminal tools.

### Pattern 2: Streaming edit (out of scope for v1)
1. Bot sends initial output message
2. Bot edits that message every N seconds with growing output
3. Marked as out of scope in PROJECT.md — full output reply only

**Confidence: HIGH** that this exists; confirmed out-of-scope for this project.

### Pattern 3: Periodic status + final result (differentiator)
1. Bot sends "Running [command]..." with timestamp
2. For commands running >10s, send heartbeat: "Still running... (15s)"
3. Final reply with full output

This is the recommended approach for long-running commands in v1 — no streaming complexity but the user is never left wondering.

**Confidence: HIGH** that this is the right v1 pattern.

---

## Security Feature Landscape

| Feature | Necessity | Implementation Approach | Confidence |
|---------|-----------|------------------------|------------|
| Discord user ID allowlist | Critical — without this, any server member executes shell | Hard-coded or config file list of allowed user IDs | HIGH |
| Guild (server) ID allowlist | Prevents bot from being added to other servers | Check on GUILD_JOIN event; leave unauthorized guilds | HIGH |
| Channel-to-machine isolation | Prevent commands in channel A from running on machine B | Enforce channel ID → agent ID mapping strictly | HIGH |
| No command echo in logs | Command content may contain secrets | Log command metadata (user, time, exit code) not content | MEDIUM |
| Agent authentication to bot | Rogue agents should not be able to spoof a machine | Shared secret / token per agent on connection | MEDIUM |
| Rate limiting per user | Prevent command flooding | Token bucket per user ID; configurable threshold | MEDIUM |
| Sensitive pattern warning | Warn when a command contains patterns like passwords | Optional; heuristic-based detection — low priority | LOW |

---

## MVP Feature Set

The minimum set that makes this product usable and trustworthy:

**Must have in v1:**
1. Shell command execution with cross-platform support (Windows + macOS)
2. Working directory persistence per channel session
3. Output returned to Discord with truncation + overflow notice
4. Code block formatting for output
5. Command timeout (30s default) with kill
6. Immediate acknowledgment of command receipt (reaction)
7. Authorized user ID allowlist enforced on every execution
8. Guild ID allowlist (bot refuses to join unauthorized servers)
9. Machine online/offline status notification
10. Agent auto-reconnect without user intervention
11. `/new-session` to reset Claude Code session
12. Claude Code session ID persistence to disk (survives bot restart)
13. `/kill` to terminate running command
14. `/status` to show agent connection state
15. Output file upload for large outputs (> Discord limit)

**Defer to later:**
- Stdin / interactive command support — high complexity, low initial need
- Command history (`/history`) — Discord scroll is the history for v1
- Command aliases — power-user, not day-1 need
- Per-message env var injection — adds state complexity
- Startup commands per machine — nice-to-have, not blocking
- Mode toggle (Claude vs shell mode) — depends on design decision; may be table stakes depending on UX choice

---

## Sources

Training data only — external search tools unavailable during this research session.

Sources informing these findings (from training data, knowledge cutoff August 2025):
- Discord developer documentation (message limits, slash command constraints, interaction token timeouts)
- Telegram bot ecosystem: termbot, pytermbot, and similar remote shell bot patterns
- IRC shellbot conventions (long-established UX patterns for chat-to-terminal)
- Discord.py library patterns and community examples
- General remote terminal UX principles (fail loudly, acknowledge fast, never silently truncate)
- Security-focused bot design patterns from the Discord developer community

**Confidence assessment by category:**
- Table stakes features: HIGH — these are universal across all chat terminal tools, well-established
- UX patterns (syntax, formatting): HIGH — Discord constraints are well-documented; patterns are stable
- Security features: HIGH — threat model is straightforward; allowlists are the obvious correct answer
- Differentiators: MEDIUM to HIGH — feature value judgments from training data, not live user research
- Anti-features: HIGH — these are failure modes observed repeatedly in the wild
- Long-running command patterns: HIGH — Discord API constraints here are known and stable
