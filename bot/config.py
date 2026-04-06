"""Bot configuration loading from .env and config.json."""
import json
import os
from dataclasses import dataclass

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


@dataclass
class BotConfig:
    """Bot configuration."""
    shared_secret: str
    ws_host: str = DEFAULT_WS_HOST
    ws_port: int = DEFAULT_WS_PORT
    heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL
    heartbeat_timeout: int = DEFAULT_HEARTBEAT_TIMEOUT
    registration_timeout: int = DEFAULT_REGISTRATION_TIMEOUT
    log_level: str = DEFAULT_LOG_LEVEL
    log_file: str = "logs/bot.log"
    log_rotation: str = DEFAULT_LOG_ROTATION
    log_retention: str = DEFAULT_LOG_RETENTION


def load_bot_config(config_path: str = "config.json") -> BotConfig:
    """Load bot configuration from .env and config.json.

    Environment variables (.env):
        SHARED_SECRET: Required. Shared secret for agent authentication.

    Config file (config.json):
        Optional. Overrides default values for websocket, heartbeat, auth, logging.

    Args:
        config_path: Path to config.json file. Defaults to "config.json".

    Returns:
        BotConfig instance with merged values.

    Raises:
        ValueError: If SHARED_SECRET is not set in environment.
    """
    load_dotenv()

    shared_secret = os.environ.get("SHARED_SECRET")
    if not shared_secret:
        raise ValueError("SHARED_SECRET environment variable is required but not set")

    # Start with defaults
    kwargs = {"shared_secret": shared_secret}

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

    return BotConfig(**kwargs)
