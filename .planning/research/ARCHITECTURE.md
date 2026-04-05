# Architecture Patterns

**Domain:** Discord bot + multi-machine terminal control system
**Researched:** 2026-04-06
**Confidence:** HIGH (subprocess patterns verified from official Python docs; WebSocket and discord.py patterns from well-established library knowledge)

---

## Recommended Architecture

### Top-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│  Discord                                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ #machine-1  │  │ #machine-2  │  │ #machine-3  │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
└─────────┼────────────────┼────────────────┼────────────────────┘
          │ discord.py gateway (WSS)          │
          ▼                                  │
┌─────────────────────────────────────────┐  │
│  BOT PROCESS (runs on user's PC/Mac)    │  │
│                                         │  │
│  DiscordClient (discord.py)             │  │
│       │                                 │  │
│  ChannelRouter                          │  │
│    channel_id → agent_id mapping        │  │
│       │                                 │  │
│  AgentRegistry                          │  │
│    agent_id → WebSocket connection      │  │
│       │                                 │  │
│  WS Server (websockets / aiohttp)       │  │
│    listens on 0.0.0.0:PORT              │  │
└─────────────────────────────────────────┘
          ▲          ▲          ▲
          │          │          │  (outbound connections from agents)
┌─────────┴──┐ ┌─────┴──┐ ┌────┴───┐
│  Agent     │ │ Agent  │ │ Agent  │
│  machine-1 │ │ mach-2 │ │ mach-3 │
│            │ │        │ │        │
│  WS client │ │ WS cl. │ │ WS cl. │
│  Executor  │ │ Exec.  │ │ Exec.  │
│  SessionMgr│ │ SessMgr│ │ SessMgr│
└────────────┘ └────────┘ └────────┘
```

---

## Component Boundaries

### Bot Process

| Component | Responsibility | File |
|-----------|---------------|------|
| `DiscordClient` | Connects to Discord gateway, receives messages, sends replies. Uses discord.py `on_message` event. | `bot/client.py` |
| `ChannelRouter` | Maps `channel_id` (int) to `agent_id` (str). Loads mapping from `config.json` at startup. Answers "which agent owns this channel?" | `bot/router.py` |
| `AgentRegistry` | Maintains live WebSocket connections keyed by `agent_id`. Handles registration, eviction on disconnect, lookup by ID. | `bot/registry.py` |
| `WsServer` | Runs the WebSocket server agents connect to. Authenticates agents with a shared secret. Dispatches inbound messages to the registry. | `bot/ws_server.py` |
| `MessageBroker` | Glues `DiscordClient` → `ChannelRouter` → `AgentRegistry`. Sends a command to the right agent; awaits the reply; posts it back to Discord. | `bot/broker.py` |
| `Config` | Loads `config.json`: WS port, shared secret, channel→agent map, allowed Discord user IDs. | `bot/config.py` |

### Agent Process (one per machine)

| Component | Responsibility | File |
|-----------|---------------|------|
| `WsClient` | Outbound WebSocket connection to bot. Sends `register` message on connect. Reconnects with exponential backoff on disconnect. | `agent/ws_client.py` |
| `Dispatcher` | Receives command messages from bot. Routes to `ShellExecutor` or `ClaudeExecutor` based on `type` field. Sends result back over the same WS connection. | `agent/dispatcher.py` |
| `ShellExecutor` | Runs arbitrary shell commands via `asyncio.create_subprocess_shell`. Captures stdout+stderr. Enforces timeout via `asyncio.wait_for`. | `agent/shell_executor.py` |
| `ClaudeExecutor` | Runs `claude -p --resume <session_id>` via `asyncio.create_subprocess_exec`. Manages session ID lifecycle — persists to `sessions.json`, clears on `/new-session`. | `agent/claude_executor.py` |
| `SessionStore` | Reads/writes `sessions.json`: maps a logical key (e.g., `"default"`) to the last Claude session ID returned by the CLI. | `agent/session_store.py` |
| `Config` | Loads `agent.json`: bot WS URL, shared secret, machine name. | `agent/config.py` |

---

## Data Flow

### 1. Agent Startup and Registration

```
Agent boots
  → WsClient connects to ws://BOT_HOST:PORT
  → sends: {"type": "register", "secret": "...", "agent_id": "machine-1"}
  → Bot.AgentRegistry stores (agent_id → ws_connection)
  → Bot replies: {"type": "registered"}
  → Agent is now live and ready for commands
```

### 2. Command Dispatch (shell or claude)

```
User types "ls -la" in #machine-1

Discord → bot.DiscordClient.on_message(msg)
  → ChannelRouter.resolve(msg.channel.id) → "machine-1"
  → AgentRegistry.get("machine-1") → ws_connection
  → MessageBroker sends over WS:
      {
        "type": "shell",          # or "claude"
        "request_id": "<uuid>",
        "payload": "ls -la"
      }

Agent.Dispatcher receives message
  → routes to ShellExecutor (or ClaudeExecutor)
  → executes command
  → sends back:
      {
        "type": "result",
        "request_id": "<uuid>",
        "stdout": "...",
        "stderr": "...",
        "exit_code": 0
      }

Bot.MessageBroker receives result (matched by request_id)
  → truncates to Discord 2000-char limit if needed
  → bot.channel.send(formatted_output)
```

### 3. Claude Session Flow

```
User sends "explain this code" in #machine-1

  → type = "claude", payload = "explain this code"
  → Agent.ClaudeExecutor reads sessions.json → session_id = "abc123" (or None)
  → Builds command:
      ["claude", "-p", "--resume", "abc123", "explain this code"]
      OR (first message):
      ["claude", "-p", "explain this code"]
  → Runs via asyncio.create_subprocess_exec, captures stdout
  → Parses new session_id from output (claude CLI prints it)
  → Writes new session_id back to sessions.json
  → Returns response text to bot

User sends "/new-session"
  → Agent.ClaudeExecutor deletes session_id from sessions.json
  → Next message starts a fresh session
```

### 4. Disconnect and Reconnect

```
Agent WS drops (network hiccup, bot restart, etc.)

Agent side:
  → WsClient catches ConnectionClosed
  → enters retry loop: wait 2s, 4s, 8s, ... (cap at 60s)
  → re-sends register message on reconnect

Bot side:
  → AgentRegistry removes dead entry on ConnectionClosed
  → If bot receives a Discord message for a disconnected agent:
      → broker posts "[machine-1 is offline — command queued or dropped]"
  → When agent reconnects, registry entry is restored

v1 decision: DROP commands when agent is offline (no queue).
Queue is a Phase 2 concern — adds complexity that isn't validated yet.
```

---

## Agent-to-Bot Communication: Why WebSocket (not HTTP long-poll or message queue)

**Verdict: WebSocket — HIGH confidence this is correct for this topology.**

| Approach | Verdict | Reason |
|----------|---------|--------|
| WebSocket (agent connects OUT to bot) | **Use this** | Agents behind NAT initiate outbound — no port forwarding needed on agent machines. Bot only needs one inbound port open. Persistent connection = low latency, bidirectional, no polling overhead. |
| HTTP long-poll | Reject | Requires agents to poll the bot repeatedly. More complex state management. Higher latency. More boilerplate. No advantage here. |
| Message queue (Redis, RabbitMQ, etc.) | Reject for v1 | Requires a third process (the broker) that must be publicly reachable or self-hosted. Massive added complexity. Appropriate when bot and agents are cloud services — not for local hardware. |
| SSH reverse tunnel | Reject | User-facing complexity: requires SSH keys, tunnel management, systemd units. Defeats the "lightweight agent" goal. |

**Key architectural implication:** The bot must listen on a port (default `8765`). The user running the bot must ensure this port is reachable from agent machines — either all on LAN, or with a port forward on the router if agents are remote. This is a setup-time concern, not a code-time concern.

---

## Channel-to-Agent Mapping

**How it works:** A `config.json` file on the bot machine stores the mapping.

```json
{
  "ws_port": 8765,
  "secret": "your-shared-secret",
  "channel_map": {
    "1234567890123456789": "machine-1",
    "9876543210987654321": "machine-2"
  },
  "allowed_users": [111222333444555666]
}
```

**Why static config (not dynamic):** Channel IDs are stable (Discord never reuses them). Allowing agents to self-register their channel ID creates a security problem — any agent that knows the secret could hijack any channel. Static config keeps the channel→machine binding under the operator's control.

**Setup flow:** User creates a channel, copies the channel ID (right-click → Copy ID in Discord developer mode), adds it to `config.json`, restarts the bot. One-time operation per machine.

**ChannelRouter at runtime:**
- On `on_message`, check `message.channel.id` against the map
- If no match: ignore the message silently (channels not in the map are not controlled channels)
- If match: return the `agent_id` string

---

## Session State Management (Claude Code)

**Where state lives:** On the agent machine, in a local `sessions.json` file.

```json
{
  "default": "session-id-returned-by-claude-cli"
}
```

**Why local file, not bot-side storage:**
- The session ID is only meaningful to the Claude CLI process on that machine
- Storing it on the bot would require a round-trip before every claude command
- The agent is authoritative for its own session state

**Session ID lifecycle:**

1. First `claude -p "prompt"` — no `--resume` flag → Claude starts fresh, prints session ID on stdout (or stderr — verify at implementation time which stream)
2. Agent parses session ID from output using a regex like `r'session[_-]?id[:\s]+([a-zA-Z0-9_-]+)'` — exact format must be verified against current `claude` CLI behavior
3. Stores it in `sessions.json`
4. All subsequent prompts use `claude -p --resume <id> "prompt"`
5. `/new-session` command → agent deletes the entry → next message starts fresh

**Confidence note:** The exact CLI flags (`--resume`, output format of session ID) must be verified against the installed `claude` CLI version at implementation time. The mechanism above is the pattern; the exact flags are LOW confidence until tested.

---

## Process Execution Architecture

**Confirmed from official Python docs (HIGH confidence):**

```python
# Shell command execution
async def run_shell(command: str, timeout: float = 30.0) -> dict:
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode,
        }
    except asyncio.TimeoutError:
        proc.kill()
        return {"stdout": "", "stderr": "Command timed out", "exit_code": -1}
```

**Windows caveat:** `asyncio.create_subprocess_shell` on Windows uses `cmd.exe` by default. For PowerShell, the command must be prefixed with `powershell -Command "..."`. The agent should detect the OS at startup and set a shell mode.

**Output size:** Discord messages are capped at 2000 characters. The bot must truncate or split long output. Strategy: send first 1900 chars, append `…[truncated]`. Streaming/pagination is out of scope for v1.

**Timeout defaults:**
- Shell commands: 30 seconds (configurable)
- Claude invocations: 120 seconds (LLM latency is unpredictable)

---

## Codebase Structure: Monorepo

**Recommendation: Monorepo with two packages under one repo — HIGH confidence this is correct for the team size and deployment model.**

```
bot_auto_all/
├── bot/                     # Discord bot (runs on one machine)
│   ├── __main__.py          # Entry point: python -m bot
│   ├── client.py            # discord.py DiscordClient
│   ├── broker.py            # MessageBroker — glue logic
│   ├── router.py            # ChannelRouter
│   ├── registry.py          # AgentRegistry
│   ├── ws_server.py         # WebSocket server
│   └── config.py            # Config loader
│
├── agent/                   # Lightweight agent (runs on each machine)
│   ├── __main__.py          # Entry point: python -m agent
│   ├── ws_client.py         # WsClient with reconnect logic
│   ├── dispatcher.py        # Command dispatcher
│   ├── shell_executor.py    # ShellExecutor
│   ├── claude_executor.py   # ClaudeExecutor
│   ├── session_store.py     # SessionStore (sessions.json)
│   └── config.py            # Config loader
│
├── shared/                  # Code shared between bot and agent
│   ├── protocol.py          # Message type constants, schema helpers
│   └── logging.py           # Shared logging setup
│
├── config.example.json      # Bot config template
├── agent.example.json       # Agent config template
├── requirements.txt         # Single requirements file
├── requirements-dev.txt     # Dev/test dependencies
└── .planning/               # GSD planning files
```

**Why monorepo over separate repos:**
- Single `git clone` to get everything — trivial for a solo/small team
- Shared `protocol.py` avoids message schema drift between bot and agent
- Single `requirements.txt` to manage
- No need for packaging/publishing — user just clones and runs

**Why not a single process:** Bot and agent have fundamentally different deployment targets. The bot runs once; agents run on N machines. Keeping them as separate entry points (`python -m bot`, `python -m agent`) makes deployment straightforward — copy only the `agent/` folder to remote machines if desired.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Storing Agent State on the Bot
**What goes wrong:** Bot tracks "what session is machine-1 running." When bot restarts, state is lost. When agent reconnects, bot and agent are out of sync.
**Instead:** Agent is authoritative for its own state. Bot is stateless except for the live connection registry (which is ephemeral by design).

### Anti-Pattern 2: Long-Running Claude Subprocess Per Channel
**What goes wrong:** Keeping a `claude` process alive between messages to maintain conversation context. Process leaks if Discord connection drops. Zombie processes on the agent machine. Requires IPC to push new prompts into a running process.
**Instead:** Invoke `claude -p --resume <session_id>` as a fresh subprocess for each message. The session ID is the continuity mechanism — the process itself is transient. This is the correct use of the `--resume` flag.

### Anti-Pattern 3: Synchronous Blocking in the Bot
**What goes wrong:** Bot uses `requests` or `socket` (sync) to talk to agents. Discord's event loop blocks while waiting for agent response. All other Discord events queue up; bot appears unresponsive.
**Instead:** Everything in the bot is async. The WS server is `asyncio`-native (`websockets` library). Agent communication uses `asyncio.Queue` or `asyncio.Future` for pending responses.

### Anti-Pattern 4: Polling Channel IDs from Discord API
**What goes wrong:** Bot calls Discord API to discover channel names and map them to agents. Rate-limited, adds latency, brittle if channels are renamed.
**Instead:** Use static `config.json` with channel IDs (not names). Channel IDs never change; names can be whatever the user wants.

### Anti-Pattern 5: Broadcasting Commands to All Agents
**What goes wrong:** Bot sends every command to all connected agents and lets them filter. No security, wasteful, any agent can see all commands.
**Instead:** Bot routes commands point-to-point via `AgentRegistry.get(agent_id)`. Only the target agent receives the command.

---

## Scalability Considerations

This system is deliberately scoped to small-group personal use. Scale is not a design constraint — but these numbers give context:

| Concern | At 5 machines | At 50 machines | At 500 machines |
|---------|---------------|----------------|-----------------|
| WS connections | Trivial | Trivial | Fine (each is idle most of the time) |
| Channel map | Static JSON | Static JSON | Consider DB |
| Concurrent commands | One per agent | One per agent | Add per-agent queue |
| Bot process | Single process fine | Single process fine | Would need sharding |
| Session storage | Local file per agent | Local file per agent | Fine |

For v1 (2-10 machines), no scaling work is needed.

---

## Suggested Build Order

**Rationale: Build the critical path first. Each phase produces something runnable. Never have a phase that only adds infrastructure.**

### Phase 1: Bot skeleton + agent WS connection
**Builds:** WS server in bot, WS client in agent with reconnect, registration handshake, config loading.
**Deliverable:** Agent connects to bot, bot logs "machine-1 registered." No Discord yet.
**Why first:** This is the hardest architectural piece. Get the agent↔bot plumbing working in isolation before adding Discord complexity. Also validates the NAT traversal assumption early.

### Phase 2: Discord bot + shell command execution
**Builds:** discord.py client, ChannelRouter, MessageBroker, ShellExecutor, full dispatch-and-reply loop.
**Deliverable:** Type a shell command in a Discord channel → see output in the same channel. End-to-end working for the primary use case.
**Why second:** The core value proposition. Everything else is enhancement.

### Phase 3: Claude Code sessions
**Builds:** ClaudeExecutor, SessionStore, `/new-session` handling, timeout tuning.
**Deliverable:** Multi-turn Claude Code conversations in a Discord channel with session continuity.
**Why third:** Depends on Phase 2's dispatch infrastructure. Claude CLI flag behavior must be verified against installed version — intentionally isolated to its own phase.

### Phase 4: Hardening + access control
**Builds:** Allowed-user enforcement, output truncation/formatting, graceful error messages, agent-offline feedback, timeout configurability, logging.
**Deliverable:** System is safe to leave running; strangers can't send commands; errors surface cleanly.
**Why fourth:** Correctness before safety is fine during development; safety before shipping is required.

### Phase 5: Packaging and setup experience
**Builds:** `config.example.json`, `agent.example.json`, startup scripts (`.bat` for Windows, shell scripts for Mac), `requirements.txt`, basic README.
**Deliverable:** A second person can set up the system from the repo without asking questions.
**Why last:** Packaging before the system is stable creates churn. Write it once, when the design is settled.

---

## Wire Protocol (Message Schema)

All messages are JSON over the WebSocket connection.

### Agent → Bot

```jsonc
// Registration
{"type": "register", "secret": "...", "agent_id": "machine-1", "platform": "win32"}

// Command result
{"type": "result", "request_id": "uuid", "stdout": "...", "stderr": "...", "exit_code": 0}

// Heartbeat (optional, Phase 4)
{"type": "ping"}
```

### Bot → Agent

```jsonc
// Acknowledgment
{"type": "registered"}

// Shell command
{"type": "shell", "request_id": "uuid", "payload": "ls -la", "timeout": 30}

// Claude command
{"type": "claude", "request_id": "uuid", "payload": "explain this code", "timeout": 120}

// Session reset
{"type": "reset_session"}

// Heartbeat response (optional, Phase 4)
{"type": "pong"}
```

**Why `request_id`:** The bot sends a command and must match the async reply to the right pending Discord message. UUIDs generated by the bot; echoed back by the agent. Bot holds a `dict[str, asyncio.Future]` mapping `request_id` → future; broker awaits the future; agent result resolves it.

---

## Sources

- Python asyncio subprocess docs (official, verified): https://docs.python.org/3/library/asyncio-subprocess.html
- discord.py library: https://discordpy.readthedocs.io (HIGH confidence — mature, stable API since 2016)
- websockets library: https://websockets.readthedocs.io (HIGH confidence — de facto standard for Python async WS)
- Wire protocol pattern: Standard JSON-RPC-inspired request/response with correlation IDs — industry standard, HIGH confidence
- NAT traversal via outbound connection: Established networking pattern, HIGH confidence
- Claude CLI `--resume` flag: MEDIUM confidence — pattern is correct, exact flag name needs verification at implementation time against installed `claude` version
