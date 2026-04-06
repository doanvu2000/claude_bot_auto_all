"""Shared package: protocol definitions and constants used by both bot and agent."""
from shared.protocol import (
    BaseMessage,
    RegisterMessage,
    AckMessage,
    ErrorMessage,
    HeartbeatPing,
    HeartbeatPong,
    DisconnectMessage,
    Message,
    parse_message,
)

__all__ = [
    "BaseMessage",
    "RegisterMessage",
    "AckMessage",
    "ErrorMessage",
    "HeartbeatPing",
    "HeartbeatPong",
    "DisconnectMessage",
    "Message",
    "parse_message",
]
