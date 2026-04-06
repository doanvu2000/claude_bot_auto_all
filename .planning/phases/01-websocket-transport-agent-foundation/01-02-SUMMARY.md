---
phase: 01-websocket-transport-agent-foundation
plan: 02
subsystem: bot-websocket-server
tags: [websocket, server, auth, heartbeat, agent-management]
dependency_graph:
  requires: [shared/protocol.py, shared/constants.py, bot/config.py]
  provides: [bot/server.py, bot/__main__.py]
  affects: [agent-connection-flow, bot-startup]
tech_stack:
  added: [websockets.asyncio.server]
  patterns: [AgentManager-pattern, heartbeat-ping-pong, shared-secret-auth]
key_files:
  created:
    - bot/server.py
    - tests/test_handshake.py
    - tests/test_server.py
  modified:
    - bot/__main__.py
    - tests/conftest.py
decisions:
  - "Used websockets 16.x asyncio API (serve from websockets.asyncio.server) -- project installed v16 not v12"
  - "signal.signal() for cross-platform shutdown instead of loop.add_signal_handler() which fails on Windows"
  - "HeartbeatPing sent only to agents past initial registration -- prevents race during auth"
metrics:
  duration: "~3 minutes"
  completed: "2026-04-07"
  tasks_completed: 1
  tasks_total: 1
  test_count: 13
  test_pass: 13
---

# Phase 01 Plan 02: Bot WebSocket Server Summary

WebSocket server with shared-secret auth, machine_name registration, heartbeat monitoring, and graceful disconnect using websockets 16.x asyncio API.

## Task Results

### Task 1: Bot WebSocket server with auth, registration, and heartbeat (TDD)

**RED:** Created 13 failing tests across `test_handshake.py` (7 tests) and `test_server.py` (6 tests). Updated `conftest.py` with `ws_server`, `bot_config`, `free_port` fixtures using fast timeouts (1s heartbeat, 3s timeout, 2s registration timeout).
- Commit: `7b22de7`

**GREEN:** Implemented `bot/server.py` with `AgentManager` class and `start_server()` function. Updated `bot/__main__.py` to use the server. All 13 tests pass, plus all 28 existing tests (41 total).
- Commit: `dd6be71`

**Key implementation details:**
- `AgentInfo` dataclass tracks websocket, machine_name, platform, last_pong timestamp
- `AgentManager._authenticate()` enforces registration timeout via `asyncio.wait_for()`, validates shared secret, rejects duplicates
- `AgentManager._heartbeat_loop()` sends `HeartbeatPing` at configurable interval, removes agents exceeding timeout
- `AgentManager._handle_agent()` processes `HeartbeatPong` (updates last_pong), `DisconnectMessage` (clean removal)
- `start_server()` uses `signal.signal()` for SIGINT/SIGTERM (Windows-compatible, no `loop.add_signal_handler()`)

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

- `py -m pytest tests/test_handshake.py tests/test_server.py -x -v` -- 13/13 passed
- `py -m pytest -x -v` -- 41/41 passed (no regressions)
- `py -c "from bot.server import AgentManager, start_server; print('OK')"` -- OK

## Acceptance Criteria Check

- [x] bot/server.py contains `class AgentManager:`
- [x] bot/server.py contains `class AgentInfo:`
- [x] bot/server.py contains `async def handler(self, websocket`
- [x] bot/server.py contains `async def _authenticate(self, websocket`
- [x] bot/server.py contains `async def _heartbeat_loop(self`
- [x] bot/server.py contains `async def start_server(`
- [x] bot/server.py contains `from websockets.asyncio.server import serve`
- [x] bot/server.py contains `reason="auth_failed"`
- [x] bot/server.py contains `reason="machine_name_taken"`
- [x] bot/server.py contains `asyncio.wait_for(` (registration timeout)
- [x] bot/server.py contains `signal.signal(signal.SIGINT` (cross-platform shutdown)
- [x] bot/__main__.py contains `from bot.server import start_server`
- [x] All tests pass

## Self-Check: PASSED

All files exist. All commits verified. All tests green.
