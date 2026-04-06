"""Tests for shared.protocol message models and parse_message."""
import json
import uuid
import pytest
from pydantic import ValidationError


class TestMessageModels:
    """Test that all 6 message types can be created and serialized."""

    def test_register_message_valid(self):
        from shared.protocol import RegisterMessage
        msg = RegisterMessage(secret="my-secret", machine_name="my-pc", platform="win32")
        assert msg.type == "register"
        assert msg.secret == "my-secret"
        assert msg.machine_name == "my-pc"
        assert msg.platform == "win32"
        # request_id should be auto-generated UUID
        uuid.UUID(msg.request_id)  # Should not raise

    def test_ack_message(self):
        from shared.protocol import AckMessage
        msg = AckMessage()
        assert msg.type == "ack"
        uuid.UUID(msg.request_id)

    def test_error_message_has_reason(self):
        from shared.protocol import ErrorMessage
        msg = ErrorMessage(reason="auth_failed")
        assert msg.type == "error"
        assert msg.reason == "auth_failed"

    def test_heartbeat_ping(self):
        from shared.protocol import HeartbeatPing
        msg = HeartbeatPing()
        assert msg.type == "heartbeat_ping"

    def test_heartbeat_pong(self):
        from shared.protocol import HeartbeatPong
        msg = HeartbeatPong()
        assert msg.type == "heartbeat_pong"

    def test_disconnect_message(self):
        from shared.protocol import DisconnectMessage
        msg = DisconnectMessage()
        assert msg.type == "disconnect"

    def test_request_id_auto_generated_uuid(self):
        from shared.protocol import RegisterMessage
        msg1 = RegisterMessage(secret="s", machine_name="m", platform="linux")
        msg2 = RegisterMessage(secret="s", machine_name="m", platform="linux")
        # Both should have valid UUIDs
        uuid.UUID(msg1.request_id)
        uuid.UUID(msg2.request_id)
        # And they should be different
        assert msg1.request_id != msg2.request_id

    def test_request_id_can_be_provided(self):
        from shared.protocol import AckMessage
        msg = AckMessage(request_id="custom-id-123")
        assert msg.request_id == "custom-id-123"


class TestRoundTrip:
    """Test all 6 message types round-trip through serialize/deserialize."""

    def test_register_round_trip(self):
        from shared.protocol import RegisterMessage, parse_message
        original = RegisterMessage(secret="s", machine_name="m", platform="win32")
        json_str = original.model_dump_json()
        parsed = parse_message(json_str)
        assert isinstance(parsed, RegisterMessage)
        assert parsed.secret == "s"
        assert parsed.machine_name == "m"
        assert parsed.request_id == original.request_id

    def test_ack_round_trip(self):
        from shared.protocol import AckMessage, parse_message
        original = AckMessage()
        parsed = parse_message(original.model_dump_json())
        assert isinstance(parsed, AckMessage)
        assert parsed.request_id == original.request_id

    def test_error_round_trip(self):
        from shared.protocol import ErrorMessage, parse_message
        original = ErrorMessage(reason="test_error")
        parsed = parse_message(original.model_dump_json())
        assert isinstance(parsed, ErrorMessage)
        assert parsed.reason == "test_error"

    def test_heartbeat_ping_round_trip(self):
        from shared.protocol import HeartbeatPing, parse_message
        original = HeartbeatPing()
        parsed = parse_message(original.model_dump_json())
        assert isinstance(parsed, HeartbeatPing)

    def test_heartbeat_pong_round_trip(self):
        from shared.protocol import HeartbeatPong, parse_message
        original = HeartbeatPong()
        parsed = parse_message(original.model_dump_json())
        assert isinstance(parsed, HeartbeatPong)

    def test_disconnect_round_trip(self):
        from shared.protocol import DisconnectMessage, parse_message
        original = DisconnectMessage()
        parsed = parse_message(original.model_dump_json())
        assert isinstance(parsed, DisconnectMessage)


class TestParseMessage:
    """Test parse_message with various inputs."""

    def test_parse_valid_register(self):
        from shared.protocol import parse_message, RegisterMessage
        raw = '{"type":"register","secret":"s","machine_name":"m","platform":"win32"}'
        msg = parse_message(raw)
        assert isinstance(msg, RegisterMessage)

    def test_parse_invalid_json_raises(self):
        from shared.protocol import parse_message
        with pytest.raises(ValidationError):
            parse_message("not valid json{{{")

    def test_parse_unknown_type_raises(self):
        from shared.protocol import parse_message
        with pytest.raises(ValidationError):
            parse_message('{"type":"unknown_type","request_id":"123"}')

    def test_parse_missing_required_field_raises(self):
        from shared.protocol import parse_message
        # RegisterMessage without secret should fail
        with pytest.raises(ValidationError):
            parse_message('{"type":"register","machine_name":"m","platform":"win32"}')
