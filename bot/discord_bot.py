"""Discord bot class with channel-to-agent routing API.

TerminalBot is the core Discord bot that manages the mapping between Discord
channels and remote agent machines. It provides the routing contract used by
slash commands (Phase 3) to determine which agent should execute a command.
"""
import asyncio

import discord
from discord.ext import commands
from loguru import logger

from bot.config import BotConfig
from bot.server import AgentManager


class TerminalBot(commands.Bot):
    """Discord bot for remote terminal control.

    Manages the relationship between Discord channels and connected agents.
    Provides two routing API methods that Phase 3 slash commands depend on:
    - get_agent_for_channel(channel_id) -> machine_name or None
    - _find_channel_for_agent(machine_name) -> channel_id or None
    """

    def __init__(self, agent_manager: AgentManager, config: BotConfig) -> None:
        intents = discord.Intents.default()  # D-19: no message_content, no members
        super().__init__(command_prefix="!", intents=intents)  # prefix unused per D-04
        self.agent_manager = agent_manager
        self.bot_config = config
        self._ready = asyncio.Event()  # track Discord readiness for notifications

    async def setup_hook(self) -> None:
        """Sync slash commands to allowed guilds (D-11: guild commands, instant sync).

        Also registers global interaction check for guild allowlist (AUTH-04 at runtime).
        """
        # Load cogs (will be created in Plan 02)
        try:
            await self.load_extension("bot.cogs.general")
        except Exception as e:
            logger.warning(f"Could not load general cog: {e}")

        # AUTH-04 RUNTIME ENFORCEMENT (addresses review concern #4):
        # This global interaction check runs on EVERY interaction, not just at startup.
        # setup_hook only syncs commands to allowed guilds (defense-in-depth layer 1).
        # This check is the authoritative runtime gate (defense-in-depth layer 2).
        @self.tree.interaction_check
        async def global_interaction_check(interaction: discord.Interaction) -> bool:
            """Runtime guild allowlist enforcement. AUTH-04.
            NOTE: This is the PRIMARY security gate. default_permissions on commands
            is UI hiding only (defense-in-depth layer 3, not authoritative)."""
            if interaction.guild_id not in self.bot_config.allowed_guild_ids:
                return False  # silently reject unauthorized guilds
            return True

        # Sync to each allowed guild (defense-in-depth: only allowed guilds get commands)
        for guild_id in self.bot_config.allowed_guild_ids:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            try:
                await self.tree.sync(guild=guild)
                logger.info(f"Synced commands to guild {guild_id}")
            except Exception as e:
                logger.error(f"Failed to sync commands to guild {guild_id}: {e}")

    async def on_ready(self) -> None:
        """Called when Discord connection is established."""
        logger.info(f"Discord bot connected as {self.user}")
        self._ready.set()

    def setup_agent_callbacks(self) -> None:
        """Wire AgentManager callbacks to Discord notification methods."""
        self.agent_manager.on_agent_connect = self._on_agent_connect
        self.agent_manager.on_agent_disconnect = self._on_agent_disconnect

    async def _on_agent_connect(self, machine_name: str, platform: str) -> None:
        """Called by AgentManager when an agent registers.

        Addresses review concern #6: all channel.send calls wrapped in try/except.
        """
        if not self._ready.is_set():
            return  # Discord not ready yet, skip notification (Pitfall 5)

        channel_id = self._find_channel_for_agent(machine_name)

        if channel_id is None:
            # D-14: auto-create channel for unmapped agent
            await self._auto_create_channel(machine_name, platform)
        else:
            channel = self.get_channel(int(channel_id))
            if channel:
                try:
                    # D-20: connect notification. Also covers D-21 reconnection
                    await channel.send(f"\U0001f7e2 **{machine_name}** connected ({platform})")
                except Exception as e:
                    logger.error(f"Failed to send connect notification for {machine_name}: {e}")

    async def _auto_create_channel(self, machine_name: str, platform: str) -> None:
        """Auto-create a Discord channel for a newly connected agent with no mapping.

        D-14: updates config.json with new mapping via save_config (lock-protected).
        ROUT-02 note: static config is extended at runtime by auto-creation, config.json
        remains the single source of truth.
        """
        if not self.bot_config.allowed_guild_ids:
            logger.warning(
                f"No allowed guilds configured, cannot auto-create channel for {machine_name}"
            )
            return

        # Use first allowed guild (RESEARCH Open Question 2 resolution)
        guild_id = self.bot_config.allowed_guild_ids[0]
        guild = self.get_guild(guild_id)
        if guild is None:
            logger.error(f"Guild {guild_id} not found in cache, cannot auto-create channel")
            return

        # Sanitize machine_name for Discord channel name
        channel_name = machine_name.lower().replace(" ", "-").replace("_", "-")
        channel_name = "".join(c for c in channel_name if c.isalnum() or c == "-")
        if not channel_name:
            channel_name = "unnamed-agent"

        # Duplicate prevention: check if channel with same name already exists
        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            # Map to existing channel instead of creating duplicate
            self.bot_config.channel_mapping[str(existing.id)] = machine_name
            await self.bot_config.save_config()
            try:
                await existing.send(
                    f"\U0001f7e2 **{machine_name}** connected ({platform})\n"
                    f"_Mapped to existing channel._"
                )
            except Exception as e:
                logger.error(
                    f"Failed to send notification in existing channel for {machine_name}: {e}"
                )
            logger.info(
                f"Mapped agent {machine_name} to existing channel #{channel_name} (ID: {existing.id})"
            )
            return

        try:
            channel = await guild.create_text_channel(channel_name)
            logger.info(
                f"Auto-created channel #{channel_name} (ID: {channel.id}) for agent {machine_name}"
            )

            # Update config mapping and persist
            self.bot_config.channel_mapping[str(channel.id)] = machine_name
            await self.bot_config.save_config()

            # Send connect notification in new channel
            await channel.send(
                f"\U0001f7e2 **{machine_name}** connected ({platform})\n"
                f"_Channel auto-created for this machine._"
            )

        except discord.Forbidden:
            logger.error(
                f"Missing manage_channels permission in guild {guild_id}, "
                f"cannot auto-create channel for {machine_name}"
            )
        except Exception as e:
            logger.error(f"Failed to auto-create channel for {machine_name}: {e}")

    async def _on_agent_disconnect(self, machine_name: str) -> None:
        """Called by AgentManager when agent disconnects. Sends notification to mapped channel.

        Addresses review concern #6: error handling on disconnect notification too.
        """
        if not self._ready.is_set():
            return
        channel_id = self._find_channel_for_agent(machine_name)
        if channel_id:
            channel = self.get_channel(int(channel_id))
            if channel:
                try:
                    await channel.send(f"\U0001f534 **{machine_name}** disconnected")
                except Exception as e:
                    logger.error(f"Failed to send disconnect notification for {machine_name}: {e}")

    def _find_channel_for_agent(self, machine_name: str) -> str | None:
        """ROUTING API: Look up channel ID for a given machine_name.

        Reverse lookup from channel_mapping (which maps channel_id -> machine_name).
        Used by notification system and will be used by Phase 3 for response routing.
        """
        for ch_id, name in self.bot_config.channel_mapping.items():
            if name == machine_name:
                return ch_id
        return None

    def get_agent_for_channel(self, channel_id: int) -> str | None:
        """ROUTING API (ROUT-01): Look up machine_name for a given Discord channel_id.

        Returns None if channel is not mapped to any agent.
        Phase 3's /run command will call this to determine which agent executes a command.
        Channel IDs from Discord are int; config stores them as string keys (Pitfall 3).
        """
        return self.bot_config.channel_mapping.get(str(channel_id))
