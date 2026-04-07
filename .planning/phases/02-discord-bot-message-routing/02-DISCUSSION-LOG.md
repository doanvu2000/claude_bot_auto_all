# Phase 2: Discord Bot & Message Routing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 02-discord-bot-message-routing
**Areas discussed:** Bot-WS Integration, Message Interpretation, Channel Mapping Config, Status & Slash Commands, Slash Command Sync, Agent Without Channel, Bot Startup Sequence, WS Drop Handling

---

## Bot-WS Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Chung 1 process | discord.py và WS server chạy chung trên cùng asyncio event loop | ✓ |
| Tách 2 process | WS server và Discord bot là 2 process riêng, giao tiếp qua IPC | |

**User's choice:** Same process, shared event loop
**Notes:** Simpler architecture, AgentManager accessed directly without IPC

---

## Message Interpretation

| Option | Description | Selected |
|--------|-------------|----------|
| Mọi tin nhắn = command | Mọi tin nhắn trong mapped channel đều là command | |
| Cần prefix (! hoặc $) | Chỉ tin nhắn bắt đầu bằng prefix mới được xử lý | |
| Slash command only | Chỉ dùng Discord slash commands | ✓ |

**User's choice:** Slash commands only
**Notes:** Safest option, no accidental command execution

### Offline Agent Response

| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral error | Bot trả lời ephemeral: "Agent [name] đang offline" | ✓ |
| Visible error | Bot gửi tin nhắn thường trong channel | |

**User's choice:** Ephemeral error

### Command Targeting

| Option | Description | Selected |
|--------|-------------|----------|
| Channel-based | Slash command chỉ hoạt động trong mapped channel, auto-target agent | ✓ |
| Parameter chọn máy | Slash command có parameter bắt buộc chọn machine | |
| Cả hai | Mapped channel auto-target, ngoài cần parameter | |

**User's choice:** Channel-based targeting

### Output Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Để Phase 3 | Phase 2 chỉ lo routing, format/truncate output là Phase 3 | ✓ |
| Xử lý luôn ở Phase 2 | Phase 2 bao gồm logic truncate + file attachment | |

**User's choice:** Defer to Phase 3

### Phase 2 Slash Commands

| Option | Description | Selected |
|--------|-------------|----------|
| /status + /help | 2 command cơ bản theo requirements | |
| Thêm /ping | /status + /help + /ping cho debugging | ✓ |
| Thêm /bind + /unbind | Config mapping qua Discord | |

**User's choice:** /status + /help + /ping (plus /reload added via channel mapping discussion)

---

## Channel Mapping Config

| Option | Description | Selected |
|--------|-------------|----------|
| Trong config.json | Thêm section channel_mapping vào config.json hiện có | ✓ |
| File riêng: channels.json | Tách mapping ra file riêng | |
| Env var + config.json | Mapping trong config.json, override bằng env var | |

**User's choice:** config.json with channel_mapping section

### Config Reload

| Option | Description | Selected |
|--------|-------------|----------|
| Restart bot | Sửa config.json rồi restart | |
| Hot-reload với /reload | Slash command /reload để reload config | ✓ |

**User's choice:** Hot-reload via /reload command

### Access Control Response

| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral reject | Trả lời ephemeral cho unauthorized user | |
| Im lặng (ignore) | Không phản hồi gì | |
| Ẩn slash commands luôn | Dùng Discord permissions để ẩn commands | ✓ |

**User's choice:** Hide slash commands from unauthorized users entirely

### Discord Token Location

| Option | Description | Selected |
|--------|-------------|----------|
| Cùng .env | Thêm DISCORD_BOT_TOKEN vào .env hiện có | |
| File .env riêng cho bot | bot/.env cho Discord token | ✓ |

**User's choice:** Separate bot/.env file

---

## Status & Slash Commands

### /status Display Format

| Option | Description | Selected |
|--------|-------------|----------|
| Embed | Discord embed với màu sắc, fields cho từng agent | ✓ |
| Plain text | Đơn giản dạng text | |

**User's choice:** Embed format

### Agent Notifications Location

| Option | Description | Selected |
|--------|-------------|----------|
| Mapped channel | Thông báo gửi vào channel được map với agent đó | ✓ |
| Channel chung (log channel) | Tất cả thông báo vào 1 channel log riêng | |
| Cả hai | Gửi vào cả mapped channel và log channel | |

**User's choice:** Mapped channel only

### /status and /help Visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral | Chỉ user gõ command thấy kết quả | |
| Visible | Cả channel thấy | ✓ |

**User's choice:** Visible to entire channel

### Discord Intents

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal intents | Chỉ guilds + guild_messages, không cần message_content | ✓ |
| Bật message_content | Thêm message_content intent dự phòng | |

**User's choice:** Minimal intents only

---

## Slash Command Sync

| Option | Description | Selected |
|--------|-------------|----------|
| Guild commands | Sync tức thì với các guild trong allowed_guild_ids | ✓ |
| Global commands | Sync 1 lần cho tất cả servers, mất ~1h | |

**User's choice:** Guild commands for instant sync

---

## Agent Without Channel

| Option | Description | Selected |
|--------|-------------|----------|
| Chấp nhận + log warning | Agent vẫn register, hiện trong /status, log warning | |
| Từ chối kết nối | Bot reject agent nếu không có channel map | |
| Tự tạo channel | Bot tự động tạo Discord channel cho agent mới | ✓ |

**User's choice:** Auto-create channel named after machine_name

### Auto-Created Channel Name

| Option | Description | Selected |
|--------|-------------|----------|
| machine-name | Tên channel = machine_name của agent | ✓ |
| Prefix + machine-name | Thêm prefix (bot-, terminal-) | |

**User's choice:** machine-name directly

---

## Bot Startup Sequence

| Option | Description | Selected |
|--------|-------------|----------|
| WS trước, Discord sau | WS server starts first, then Discord bot connects | ✓ |
| Song song | Cả hai khởi động cùng lúc bằng asyncio.gather() | |

**User's choice:** WS server first, then Discord

---

## WS Drop Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Heartbeat detect + notify | Heartbeat phát hiện trong 30s, thông báo mapped channel | ✓ |
| Instant detect + notify | WebSocket close event detect ngay | |

**User's choice:** Heartbeat-based detection (30s) with channel notification

---

## Claude's Discretion

- Exact embed color scheme and field layout
- Discord channel category for auto-created channels
- Error message wording details
- /reload permission scope
- /ping response format

## Deferred Ideas

- TLS/WSS encryption — Phase 5
- Rate limiting per user — Phase 5
- Shell execution — Phase 3
- Claude Code sessions — Phase 4
- Output truncation — Phase 3
- Role-based permissions — v2
