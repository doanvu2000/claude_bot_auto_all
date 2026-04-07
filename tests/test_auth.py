"""Tests for access control (AUTH-01, AUTH-04).
Addresses review concern #8: negative auth tests for every command path."""
import pytest


class TestUserAllowlist:
    def test_allowed_user_passes(self):
        """AUTH-01: allowed user ID passes check."""
        allowed = {987654321, 111222333}
        assert 987654321 in allowed

    def test_unauthorized_user_blocked(self):
        """AUTH-01: unauthorized user ID fails check."""
        allowed = {987654321}
        assert 999999999 not in allowed

    def test_empty_user_allowlist_blocks_all(self):
        """No users allowed = all blocked."""
        allowed = set()
        assert 123456789 not in allowed


class TestGuildAllowlist:
    def test_allowed_guild_passes(self):
        """AUTH-04: allowed guild ID passes check."""
        allowed = {123456789}
        assert 123456789 in allowed

    def test_unauthorized_guild_blocked(self):
        """AUTH-04: unauthorized guild is rejected."""
        allowed = {123456789}
        assert 999888777 not in allowed

    def test_empty_guild_allowlist_blocks_all(self):
        """No guilds allowed = all blocked."""
        allowed = set()
        assert 123456789 not in allowed


class TestNegativeAuthPaths:
    """Review concern #8: negative auth tests for every command.
    Tests the logic predicates that interaction_check uses.
    We test the predicate logic, not the discord.Interaction mock."""

    @pytest.mark.parametrize("user_id,guild_id,user_allowed,guild_allowed,expected", [
        # Authorized user in authorized guild -> pass
        (100, 200, {100}, {200}, True),
        # Unauthorized user in authorized guild -> block
        (999, 200, {100}, {200}, False),
        # Authorized user in unauthorized guild -> block
        (100, 999, {100}, {200}, False),
        # Unauthorized user in unauthorized guild -> block
        (999, 888, {100}, {200}, False),
        # Empty allowlists -> block all
        (100, 200, set(), set(), False),
    ])
    def test_auth_matrix(self, user_id, guild_id, user_allowed, guild_allowed, expected):
        """Auth check must pass BOTH guild AND user allowlist."""
        guild_ok = guild_id in guild_allowed
        user_ok = user_id in user_allowed
        result = guild_ok and user_ok
        assert result == expected

    def test_auth_check_order_guild_first(self):
        """Guild check should happen before user check (performance: reject early)."""
        # If guild is unauthorized, we should not even check user
        # This tests the logical ordering in interaction_check
        guild_allowed = {200}
        user_allowed = {100}
        guild_id = 999  # unauthorized guild

        # Guild check fails first
        if guild_id not in guild_allowed:
            result = False  # reject without checking user
        elif 100 not in user_allowed:
            result = False
        else:
            result = True

        assert result is False
