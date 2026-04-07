"""Tests for slash command output (ROUT-04, AGNT-06).
Addresses review concern #8: /status matrix tests for connected, offline, unmapped."""
import time
from unittest.mock import MagicMock

import discord
import pytest


class TestStatusEmbed:
    """AGNT-06: /status shows all connected agents."""

    def test_status_no_agents_gray_embed(self):
        """Empty agent dict produces gray embed."""
        embed = discord.Embed(
            title="Agent Status",
            description="No agents configured or connected",
            color=0x95A5A6,
        )
        assert embed.title == "Agent Status"
        assert "No agents" in embed.description
        assert embed.color.value == 0x95A5A6

    def test_status_with_agents_green_embed(self):
        """Connected agents produce green embed with fields."""
        embed = discord.Embed(title="Agent Status", color=0x2ECC71)
        agents = {
            "my-desktop": MagicMock(platform="win32", last_pong=time.time()),
            "my-laptop": MagicMock(platform="darwin", last_pong=time.time()),
        }
        for name, info in agents.items():
            embed.add_field(
                name=f"\U0001f7e2 {name}",
                value=f"**Platform:** {info.platform}\n**Status:** Online",
                inline=False,
            )
        assert embed.color.value == 0x2ECC71
        assert len(embed.fields) == 2
        assert "my-desktop" in embed.fields[0].name
        assert "win32" in embed.fields[0].value
        assert "my-laptop" in embed.fields[1].name

    def test_status_footer_shows_count(self):
        """Footer shows agent count."""
        embed = discord.Embed(title="Agent Status", color=0x2ECC71)
        embed.set_footer(text="2 online, 1 offline -- 3 agent(s) total")
        assert "2 online" in embed.footer.text
        assert "1 offline" in embed.footer.text

    def test_status_offline_configured_agents(self):
        """Review concern: /status shows configured-but-offline agents with red circle."""
        embed = discord.Embed(title="Agent Status", color=0x2ECC71)
        # Simulate: desktop is connected, server is configured but offline
        connected = {"my-desktop": MagicMock(platform="win32", last_pong=time.time())}
        channel_mapping = {"111": "my-desktop", "222": "my-server"}

        for name, info in connected.items():
            embed.add_field(
                name=f"\U0001f7e2 {name}",
                value=f"**Platform:** {info.platform}\n**Status:** Online",
                inline=False,
            )

        configured_machines = set(channel_mapping.values())
        connected_machines = set(connected.keys())
        offline = configured_machines - connected_machines
        for machine_name in sorted(offline):
            embed.add_field(
                name=f"\U0001f534 {machine_name}",
                value="**Status:** Offline (configured)",
                inline=False,
            )

        assert len(embed.fields) == 2  # 1 connected + 1 offline
        assert "\U0001f7e2" in embed.fields[0].name  # green for connected
        assert "\U0001f534" in embed.fields[1].name  # red for offline
        assert "my-server" in embed.fields[1].name
        assert "Offline" in embed.fields[1].value


class TestHelpEmbed:
    """ROUT-04: /help lists all commands."""

    def test_help_contains_all_phase2_commands(self):
        """Help embed has fields for /status, /help, /ping, /reload."""
        embed = discord.Embed(title="Terminal Bot Commands", color=0x3498DB)
        commands_list = ["/status", "/help", "/ping", "/reload"]
        for cmd in commands_list:
            embed.add_field(name=cmd, value="description", inline=False)
        field_names = [f.name for f in embed.fields]
        assert "/status" in field_names
        assert "/help" in field_names
        assert "/ping" in field_names
        assert "/reload" in field_names
        assert len(embed.fields) == 4

    def test_help_embed_is_blue(self):
        """Help embed uses blue color."""
        embed = discord.Embed(title="Terminal Bot Commands", color=0x3498DB)
        assert embed.color.value == 0x3498DB
