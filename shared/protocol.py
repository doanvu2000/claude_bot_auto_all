"""Pydantic message models and parse_message function for the WebSocket protocol.

All messages use a discriminated union on the 'type' field. Each message has
an auto-generated UUID request_id for request/response correlation.
"""
import uuid
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter


class BaseMessage(BaseModel):
    """Base class for all protocol messages."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class RegisterMessage(BaseMessage):
    """Agent -> Bot: Register with auth secret and machine metadata."""
    type: Literal["register"] = "register"
    secret: str
    machine_name: str
    platform: str  # "win32", "darwin", "linux"


class AckMessage(BaseMessage):
    """Bot -> Agent: Acknowledge a successful operation."""
    type: Literal["ack"] = "ack"


class ErrorMessage(BaseMessage):
    """Bot -> Agent: Report an error with a reason string."""
    type: Literal["error"] = "error"
    reason: str


class HeartbeatPing(BaseMessage):
    """Bot -> Agent: Heartbeat ping to check liveness."""
    type: Literal["heartbeat_ping"] = "heartbeat_ping"


class HeartbeatPong(BaseMessage):
    """Agent -> Bot: Heartbeat pong response."""
    type: Literal["heartbeat_pong"] = "heartbeat_pong"


class DisconnectMessage(BaseMessage):
    """Agent -> Bot: Graceful disconnect notification."""
    type: Literal["disconnect"] = "disconnect"


# Discriminated union of all message types
Message = Annotated[
    Union[
        RegisterMessage,
        AckMessage,
        ErrorMessage,
        HeartbeatPing,
        HeartbeatPong,
        DisconnectMessage,
    ],
    Field(discriminator="type"),
]

# Create TypeAdapter once at module level for performance
_message_adapter = TypeAdapter(Message)


def parse_message(raw: str) -> BaseMessage:
    """Parse a JSON string into a typed message.

    Args:
        raw: JSON string representing a protocol message.

    Returns:
        A typed message instance (RegisterMessage, AckMessage, etc.)

    Raises:
        pydantic.ValidationError: If JSON is invalid or doesn't match any message type.
    """
    return _message_adapter.validate_json(raw)
