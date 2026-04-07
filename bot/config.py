"""Bot configuration loading from .env and config.json."""
import asyncio
import json
import os

import aiofiles
from dotenv import load_dotenv

from shared.constants import (
    DEFAULT_HEARTBEAT_INTERVAL,
    DEFAULT_HEARTBEAT_TIMEOUT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_RETENTION,
    DEFAULT_LOG_ROTATION,
    DEFAULT_REGISTRATION_TIMEOUT,
    DEFAULT_WS_HOST,
    DEFAULT_WS_PORT,
)


class BotConfig:
    """Bot configuration.

    Holds all configuration for the bot: WebSocket server settings, heartbeat,
    logging, Discord token, channel mapping, and guild/user allowlists.

    The _config_lock is shared by save_config and reload_config to prevent
    concurrent read/write race conditions.
    """

    def __init__(
        self,
        shared_secret: str,
        ws_host: str = DEFAULT_WS_HOST,
        ws_port: int = DEFAULT_WS_PORT,
        heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
        heartbeat_timeout: int = DEFAULT_HEARTBEAT_TIMEOUT,
        registration_timeout: int = DEFAULT_REGISTRATION_TIMEOUT,
        log_level: str = DEFAULT_LOG_LEVEL,
        log_file: str = "logs/bot.log",
        log_rotation: str = DEFAULT_LOG_ROTATION,
        log_retention: str = DEFAULT_LOG_RETENTION,
        discord_token: str = "",
        allowed_guild_ids: list[int] | None = None,
        allowed_user_ids: list[int] | None = None,
        channel_mapping: dict[str, str] | None = None,
        config_path: str = "config.json",
    ) -> None:
        self.shared_secret = shared_secret
        self.ws_host = ws_host
        self.ws_port = ws_port
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.registration_timeout = registration_timeout
        self.log_level = log_level
        self.log_file = log_file
        self.log_rotation = log_rotation
        self.log_retention = log_retention
        self.discord_token = discord_token
        self.allowed_guild_ids: list[int] = allowed_guild_ids or []
        self.allowed_user_ids: list[int] = allowed_user_ids or []
        self.channel_mapping: dict[str, str] = channel_mapping or {}
        self.config_path = config_path
        self._config_lock = asyncio.Lock()

    async def save_config(self) -> None:
        """Save current channel_mapping back to config.json.

        Acquires _config_lock to prevent concurrent read/write with reload_config.
        Re-reads the full JSON first to preserve other sections, then updates
        only the discord.channel_mapping key.
        """
        async with self._config_lock:
            # Re-read full config to preserve other sections
            async with aiofiles.open(self.config_path, "r") as f:
                content = await f.read()
            data = json.loads(content)

            # Update only channel_mapping
            if "discord" not in data:
                data["discord"] = {}
            data["discord"]["channel_mapping"] = self.channel_mapping

            # Write back atomically
            new_content = json.dumps(data, indent=4) + "\n"
            async with aiofiles.open(self.config_path, "w") as f:
                await f.write(new_content)

    async def reload_config(self) -> None:
        """Reload mutable config fields from config.json.

        Acquires _config_lock to prevent concurrent read/write with save_config.
        Updates allowed_guild_ids, allowed_user_ids, and channel_mapping in place.
        Does NOT update discord_token (requires restart).

        Raises:
            ValueError: If config.json contains invalid JSON.
        """
        async with self._config_lock:
            async with aiofiles.open(self.config_path, "r") as f:
                content = await f.read()
            data = json.loads(content)

            discord_cfg = data.get("discord", {})
            self.allowed_guild_ids = [
                int(gid) for gid in discord_cfg.get("allowed_guild_ids", [])
            ]
            self.allowed_user_ids = [
                int(uid) for uid in discord_cfg.get("allowed_user_ids", [])
            ]
            self.channel_mapping = {
                str(k): str(v)
                for k, v in discord_cfg.get("channel_mapping", {}).items()
            }


def load_bot_config(config_path: str = "config.json") -> BotConfig:
    """Load bot configuration from .env and config.json.

    Environment variables (.env):
        SHARED_SECRET: Required. Shared secret for agent authentication.
        DISCORD_BOT_TOKEN: Required. Discord bot token from bot/.env.

    Config file (config.json):
        Optional. Overrides default values for websocket, heartbeat, auth,
        logging, and discord settings.

    Args:
        config_path: Path to config.json file. Defaults to "config.json".

    Returns:
        BotConfig instance with merged values.

    Raises:
        ValueError: If SHARED_SECRET or DISCORD_BOT_TOKEN is not set in environment.
    """
    # Load both root .env and bot/.env
    load_dotenv()
    load_dotenv(dotenv_path="bot/.env")

    shared_secret = os.environ.get("SHARED_SECRET")
    if not shared_secret:
        raise ValueError("SHARED_SECRET environment variable is required but not set")

    discord_token = os.environ.get("DISCORD_BOT_TOKEN")
    if not discord_token:
        raise ValueError(
            "DISCORD_BOT_TOKEN environment variable is required but not set"
        )

    # Start with defaults
    kwargs: dict = {
        "shared_secret": shared_secret,
        "discord_token": discord_token,
        "config_path": config_path,
    }

    # Override with config.json values if file exists
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = json.load(f)

        ws = data.get("websocket", {})
        if "host" in ws:
            kwargs["ws_host"] = ws["host"]
        if "port" in ws:
            kwargs["ws_port"] = ws["port"]

        hb = data.get("heartbeat", {})
        if "interval_seconds" in hb:
            kwargs["heartbeat_interval"] = hb["interval_seconds"]
        if "timeout_seconds" in hb:
            kwargs["heartbeat_timeout"] = hb["timeout_seconds"]

        auth = data.get("auth", {})
        if "registration_timeout_seconds" in auth:
            kwargs["registration_timeout"] = auth["registration_timeout_seconds"]

        logging_cfg = data.get("logging", {})
        if "level" in logging_cfg:
            kwargs["log_level"] = logging_cfg["level"]
        if "file" in logging_cfg:
            kwargs["log_file"] = logging_cfg["file"]
        if "rotation" in logging_cfg:
            kwargs["log_rotation"] = logging_cfg["rotation"]
        if "retention" in logging_cfg:
            kwargs["log_retention"] = logging_cfg["retention"]

        # Discord config
        discord_cfg = data.get("discord", {})
        kwargs["allowed_guild_ids"] = [
            int(gid) for gid in discord_cfg.get("allowed_guild_ids", [])
        ]
        kwargs["allowed_user_ids"] = [
            int(uid) for uid in discord_cfg.get("allowed_user_ids", [])
        ]
        kwargs["channel_mapping"] = {
            str(k): str(v)
            for k, v in discord_cfg.get("channel_mapping", {}).items()
        }

    return BotConfig(**kwargs)
