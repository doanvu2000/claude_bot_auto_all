"""General slash commands for the Terminal Bot.

Provides /status, /help, /ping, /reload commands with access control.
Access control model:
- interaction_check is the PRIMARY security gate (AUTH-01 user, AUTH-04 guild)
- default_permissions(administrator=True) is UI hiding only (defense-in-depth)
"""
import time

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger


@app_commands.default_permissions(administrator=True)  # UI HIDING ONLY -- not authoritative. See interaction_check below.
class GeneralCog(commands.Cog):
    """Phase 2 slash commands. Access control enforced via interaction_check (primary)
    and default_permissions (UI hiding, defense-in-depth only)."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """PRIMARY security gate for all commands in this cog.

        AUTH-01: user allowlist. AUTH-04: guild allowlist (backup to global tree check).
        NOTE: default_permissions(administrator=True) above is UI hiding only --
        it makes commands invisible to non-admin Discord users but does NOT enforce
        authorization. This method is the real enforcement.
        """
        # AUTH-04: guild allowlist (also checked by global tree.interaction_check from Plan 01)
        if interaction.guild_id not in self.bot.bot_config.allowed_guild_ids:
            return False  # silently ignore unauthorized guild

        # AUTH-01: user allowlist -- this is the primary user-level auth gate
        if interaction.user.id not in self.bot.bot_config.allowed_user_ids:
            await interaction.response.send_message(
                "You are not authorized to use this bot.", ephemeral=True
            )
            return False

        return True

    @app_commands.command(name="status", description="Show all connected agents")
    async def status(self, interaction: discord.Interaction) -> None:
        """Show all agents: connected-mapped, connected-unmapped, and configured-but-offline.

        D-08: slash command. D-09: embed response. D-10: visible (not ephemeral).
        AGNT-06: agent status reporting.
        """
        agents = self.bot.agent_manager.agents
        channel_mapping = self.bot.bot_config.channel_mapping

        embed = discord.Embed(
            title="Agent Status",
            color=0x2ECC71 if agents else 0x95A5A6,
        )

        if not agents and not channel_mapping:
            embed.description = "No agents configured or connected"
            embed.set_footer(text="0 agent(s)")
            await interaction.response.send_message(embed=embed)  # D-10: visible
            return

        # Show connected agents
        for name, info in agents.items():
            seconds_ago = int(time.time() - info.last_pong)
            has_channel = self.bot._find_channel_for_agent(name) is not None
            status_note = "Mapped" if has_channel else "No channel mapped"
            embed.add_field(
                name=f"\U0001f7e2 {name}",
                value=(
                    f"**Platform:** {info.platform}\n"
                    f"**Status:** Online ({status_note})\n"
                    f"**Last seen:** {seconds_ago}s ago"
                ),
                inline=False,
            )

        # Show configured-but-offline agents (in channel_mapping but not in agents dict)
        configured_machines = set(channel_mapping.values())
        connected_machines = set(agents.keys())
        offline_machines = configured_machines - connected_machines
        for machine_name in sorted(offline_machines):
            embed.add_field(
                name=f"\U0001f534 {machine_name}",
                value="**Status:** Offline (configured)",
                inline=False,
            )

        total = len(agents) + len(offline_machines)
        embed.set_footer(
            text=f"{len(agents)} online, {len(offline_machines)} offline -- {total} agent(s) total"
        )
        await interaction.response.send_message(embed=embed)  # D-10: visible, not ephemeral

    @app_commands.command(name="help", description="List all available bot commands")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """List available commands as embed. D-08, D-09, D-10, ROUT-04."""
        embed = discord.Embed(
            title="Terminal Bot Commands",
            description="Available slash commands:",
            color=0x3498DB,
        )
        embed.add_field(
            name="/status",
            value="Show all connected agents and their state",
            inline=False,
        )
        embed.add_field(
            name="/help",
            value="Show this help message",
            inline=False,
        )
        embed.add_field(
            name="/ping",
            value="Bot health check -- shows latency",
            inline=False,
        )
        embed.add_field(
            name="/reload",
            value="Hot-reload config.json without restart",
            inline=False,
        )
        embed.set_footer(text="More commands coming in future phases")
        await interaction.response.send_message(embed=embed)  # D-10: visible

    @app_commands.command(name="ping", description="Bot health check")
    async def ping(self, interaction: discord.Interaction) -> None:
        """Bot health check returning latency. D-08."""
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! Latency: {latency}ms")

    @app_commands.command(name="reload", description="Hot-reload config.json")
    async def reload(self, interaction: discord.Interaction) -> None:
        """Hot-reload config.json without restart. D-08, D-13.

        Uses async reload_config with lock protection to prevent concurrent
        read/write race conditions.
        """
        try:
            await self.bot.bot_config.reload_config()
            # Re-sync commands to any new guilds added in config
            for guild_id in self.bot.bot_config.allowed_guild_ids:
                guild_obj = discord.Object(id=guild_id)
                self.bot.tree.copy_global_to(guild=guild_obj)
                await self.bot.tree.sync(guild=guild_obj)
            await interaction.response.send_message(
                "Config reloaded successfully.", ephemeral=True
            )
            logger.info(f"Config reloaded by {interaction.user}")
        except Exception as e:
            await interaction.response.send_message(
                f"Reload failed: {e}", ephemeral=True
            )
            logger.error(f"Config reload failed: {e}")


async def setup(bot: commands.Bot) -> None:
    """Required by discord.py for load_extension."""
    await bot.add_cog(GeneralCog(bot))
