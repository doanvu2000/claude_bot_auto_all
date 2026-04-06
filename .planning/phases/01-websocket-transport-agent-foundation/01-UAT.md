---
status: testing
phase: 01-websocket-transport-agent-foundation
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md]
started: 2026-04-07T12:00:00Z
updated: 2026-04-07T12:00:00Z
---

## Current Test

number: 1
name: Cold Start Smoke Test
expected: |
  Kill any running bot/agent processes. Run `py -m pytest -x -v` from the project root. All 53 tests pass with no import errors or missing dependencies.
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running bot/agent processes. Run `py -m pytest -x -v` from the project root. All 53 tests pass with no import errors or missing dependencies.
result: [pending]

### 2. Bot Server Starts
expected: Run `py -m bot` from the project root (with a valid `.env` containing SHARED_SECRET). Server prints a startup log line showing it's listening on the configured WebSocket port (default 8765). No crash or import error.
result: [pending]

### 3. Agent Connects and Registers
expected: With the bot server running, run `py -m agent` (with matching SHARED_SECRET and a MACHINE_NAME in `.env`). Agent connects, registers, and bot logs show the machine name registered. Agent stays connected (no disconnect/crash).
result: [pending]

### 4. Heartbeat Keepalive
expected: With bot and agent both running, wait ~10-15 seconds. Bot sends HeartbeatPing, agent responds with HeartbeatPong. Neither side disconnects. No timeout errors in logs.
result: [pending]

### 5. Agent Reconnects After Bot Restart
expected: With bot and agent running, kill the bot process (Ctrl+C). Agent logs show connection lost and reconnection attempts with backoff. Restart bot. Agent reconnects and re-registers automatically. Bot logs show the agent registered again.
result: [pending]

### 6. Auth Rejection with Wrong Secret
expected: Start the bot. Start an agent with a DIFFERENT SHARED_SECRET than the bot. Agent gets rejected — bot logs show auth failure, agent logs show connection closed. Agent does NOT stay connected.
result: [pending]

### 7. Graceful Agent Disconnect
expected: With bot and agent running, send SIGINT to the agent (Ctrl+C). Agent sends a DisconnectMessage before closing. Bot logs show the agent was removed cleanly (not timed out).
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps

[none yet]
