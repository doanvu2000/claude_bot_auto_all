# Phase 1: WebSocket Transport & Agent Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 01-websocket-transport-agent-foundation
**Areas discussed:** Cấu trúc project, Giao thức WebSocket, Xác thực agent, Chiến lược reconnect, Config & Environment, Logging & Error handling, Testing strategy, Registration handshake flow, Port & network config, Concurrent agents, Agent metadata, Graceful shutdown, Security hardening

---

## Cấu trúc project

| Option | Description | Selected |
|--------|-------------|----------|
| Monorepo chung thư mục | bot/ và agent/ cạnh nhau, shared/ chứa protocol chung | ✓ |
| Tách package riêng | Mỗi phần là 1 package riêng | |
| Single file | bot.py và agent.py ở root | |

**User's choice:** Monorepo chung thư mục
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| python -m bot / python -m agent | Dùng __main__.py, chạy như module | ✓ |
| python bot.py / python agent.py | Chạy trực tiếp file script | |
| Claude quyết định | Linh hoạt | |

**User's choice:** python -m bot / python -m agent

| Option | Description | Selected |
|--------|-------------|----------|
| requirements.txt | Một file chung cho cả bot và agent | ✓ |
| pyproject.toml + uv/pip | Modern Python packaging | |
| Claude quyết định | Linh hoạt | |

**User's choice:** requirements.txt

---

## Giao thức WebSocket

| Option | Description | Selected |
|--------|-------------|----------|
| JSON envelope đơn giản | Dễ debug, dễ mở rộng | |
| JSON với Pydantic validation | Validate bằng Pydantic model. Chặt chẽ hơn | ✓ |
| MessagePack (binary) | Nhỏ hơn JSON nhưng khó debug | |

**User's choice:** JSON với Pydantic validation

| Option | Description | Selected |
|--------|-------------|----------|
| UUID request_id | Mỗi command gửi kèm UUID | ✓ |
| Incremental counter | Số tăng dần | |
| Claude quyết định | Linh hoạt | |

**User's choice:** UUID request_id

| Option | Description | Selected |
|--------|-------------|----------|
| Tối thiểu: register, heartbeat, ack, error | Chỉ những gì cần cho Phase 1 | ✓ |
| Đầy đủ: register, heartbeat, command, response, error, status | Chuẩn bị sẵn cho Phase 3 | |
| Claude quyết định | Linh hoạt | |

**User's choice:** Tối thiểu — command/response thêm ở Phase 3

| Option | Description | Selected |
|--------|-------------|----------|
| Ping mỗi 15s, timeout 30s | 2 ping miss = dead | ✓ |
| Ping mỗi 10s, timeout 30s | 3 ping miss = dead | |
| Claude quyết định | Linh hoạt | |

**User's choice:** Ping mỗi 15s, timeout 30s

---

## Xác thực agent

| Option | Description | Selected |
|--------|-------------|----------|
| Trong message register đầu tiên | Agent gửi register kèm secret | ✓ |
| HTTP header khi connect | Token trong Authorization header | |
| Query parameter | ws://host:port?token=xxx | |

**User's choice:** Trong message register đầu tiên

| Option | Description | Selected |
|--------|-------------|----------|
| Đóng connection với error message | Gửi error rồi close | ✓ |
| Đóng im lặng | Close không gửi gì | |
| Claude quyết định | Linh hoạt | |

**User's choice:** Đóng connection với error message

---

## Chiến lược reconnect

| Option | Description | Selected |
|--------|-------------|----------|
| 1s → 2s → 4s → ... max 60s + jitter | Bắt đầu 1s, nhân đôi, cap ở 60s | ✓ |
| 2s → 4s → 8s → ... max 120s + jitter | Bắt đầu chậm hơn | |
| Claude quyết định | Linh hoạt | |

**User's choice:** 1s → 2s → 4s → ... max 60s + jitter

---

## Config & Environment

| Option | Description | Selected |
|--------|-------------|----------|
| .env + config.json | Secrets trong .env, settings trong config.json | ✓ |
| Chỉ .env | Tất cả trong .env | |
| Chỉ config.json | Tất cả trong JSON | |

**User's choice:** .env + config.json

**Examples:** Có cả .env.example và config.example.json

---

## Logging & Error handling

**Logging:** loguru
**WS errors:** Log + tiếp tục (one agent failure doesn't affect others)

---

## Testing

**Approach:** pytest + pytest-asyncio

---

## Registration handshake

**Flow:** 1-step — register kèm auth trong cùng 1 message
**Timeout:** 10s — đóng connection nếu không nhận register

---

## Port & network config

**Default port:** 8765
**Bind address:** 0.0.0.0

---

## Concurrent agents

**Duplicate name:** Reject cái sau (machine name là unique key)
**Max agents:** Không giới hạn

---

## Agent metadata

**Info gửi khi register:** machine_name + platform (win32/darwin/linux)

---

## Graceful shutdown

**Behavior:** Agent gửi {type: "disconnect"} trước khi tắt

---

## Security hardening

**TLS:** Không trong Phase 1 — ws:// plain
**Rate limit:** Không trong Phase 1

---

## Claude's Discretion

- Heartbeat direction (bot ping hoặc bidirectional)
- Max retry behavior (retry forever hoặc give up)
- Pydantic model structure
- Log rotation settings
- Backoff jitter implementation
