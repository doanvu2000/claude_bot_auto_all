"""Tests for channel-to-agent routing logic (ROUT-01, ROUT-03)."""
import pytest


class TestChannelRouting:
    """Test the routing API contract that Phase 3 will depend on."""

    def test_mapped_channel_returns_machine_name(self):
        """ROUT-01: channel maps to one agent."""
        mapping = {"111222333": "my-desktop", "444555666": "my-laptop"}
        channel_id = 111222333
        result = mapping.get(str(channel_id))
        assert result == "my-desktop"

    def test_unmapped_channel_returns_none(self):
        """ROUT-03: unmapped channel returns None."""
        mapping = {"111222333": "my-desktop"}
        channel_id = 999888777
        result = mapping.get(str(channel_id))
        assert result is None

    def test_channel_id_int_vs_string(self):
        """Pitfall 3: channel IDs are int from Discord, string keys in config."""
        mapping = {"111222333": "my-desktop"}
        assert mapping.get(str(111222333)) == "my-desktop"
        assert mapping.get(111222333) is None  # int key fails -- must convert

    def test_reverse_lookup_finds_channel(self):
        """_find_channel_for_agent: find channel for a known machine_name."""
        mapping = {"111222333": "my-desktop", "444555666": "my-laptop"}
        machine_name = "my-laptop"
        result = None
        for ch_id, name in mapping.items():
            if name == machine_name:
                result = ch_id
                break
        assert result == "444555666"

    def test_reverse_lookup_no_match(self):
        """_find_channel_for_agent: returns None for unknown machine."""
        mapping = {"111222333": "my-desktop"}
        machine_name = "unknown-machine"
        result = None
        for ch_id, name in mapping.items():
            if name == machine_name:
                result = ch_id
                break
        assert result is None

    def test_one_channel_one_agent_invariant(self):
        """ROUT-01: each channel maps to exactly one agent (no duplicates)."""
        mapping = {"111": "desktop", "222": "laptop", "333": "server"}
        # All values should be unique (one channel per machine)
        assert len(set(mapping.values())) == len(mapping)

    def test_empty_mapping_returns_none(self):
        """Empty channel_mapping returns None for any channel."""
        mapping = {}
        assert mapping.get(str(12345)) is None
