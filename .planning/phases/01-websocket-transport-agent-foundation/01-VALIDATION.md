---
phase: 1
slug: websocket-transport-agent-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | INFR-03 | — | N/A | unit | `python -m pytest tests/test_protocol.py -x -q` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | INFR-04 | — | N/A | unit | `python -m pytest tests/test_config.py -x -q` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | INFR-01, AUTH-02 | T-1-01 | Reject invalid secret | integration | `python -m pytest tests/test_server.py -x -q` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | AGNT-02, AGNT-05 | — | N/A | integration | `python -m pytest tests/test_server.py -x -q` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 2 | AGNT-01, AGNT-04 | — | N/A | integration | `python -m pytest tests/test_agent.py -x -q` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 2 | INFR-02 | — | N/A | integration | `python -m pytest tests/test_integration.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (event loop, free port, mock config)
- [ ] `tests/test_protocol.py` — stubs for message validation
- [ ] `tests/test_config.py` — stubs for config loading
- [ ] `tests/test_server.py` — stubs for WS server + auth
- [ ] `tests/test_agent.py` — stubs for agent reconnect
- [ ] `tests/test_integration.py` — stubs for full handshake flow
- [ ] `pip install pytest pytest-asyncio` — framework install

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-platform agent startup | AGNT-01 | Needs real Windows + macOS | Run `python -m agent` on both OS, verify connection |
| NAT traversal | INFR-01 | Needs real network topology | Agent on different network connects to bot |
