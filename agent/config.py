"""Agent configuration loading from .env and config.json."""
import json
import os
import platform
from dataclasses import dataclass

from dotenv import load_dotenv

from shared.constants import (
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_RETENTION,
    DEFAULT_LOG_ROTATION,
    DEFAULT_WS_PORT,
)


@dataclass
class AgentConfig:
    """Agent configuration."""
    shared_secret: str
    bot_url: str = f"ws://localhost:{DEFAULT_WS_PORT}"
    machine_name: str = ""
    log_level: str = DEFAULT_LOG_LEVEL
    log_file: str = "logs/agent.log"
    log_rotation: str = DEFAULT_LOG_ROTATION
    log_retention: str = DEFAULT_LOG_RETENTION


def load_agent_config(config_path: str = "config.json") -> AgentConfig:
    """Load agent configuration from .env and config.json.

    Environment variables (.env):
        SHARED_SECRET: Required. Shared secret for bot authentication.
        MACHINE_NAME: Optional. Defaults to platform.node() (hostname).
        BOT_URL: Optional. WebSocket URL of the bot. Defaults to ws://localhost:8765.

    Config file (config.json):
        Optional. Overrides default values for logging settings.

    Args:
        config_path: Path to config.json file. Defaults to "config.json".

    Returns:
        AgentConfig instance with merged values.

    Raises:
        ValueError: If SHARED_SECRET is not set in environment.
    """
    load_dotenv()

    shared_secret = os.environ.get("SHARED_SECRET")
    if not shared_secret:
        raise ValueError("SHARED_SECRET environment variable is required but not set")

    machine_name = os.environ.get("MACHINE_NAME", platform.node())
    bot_url = os.environ.get("BOT_URL", f"ws://localhost:{DEFAULT_WS_PORT}")

    kwargs = {
        "shared_secret": shared_secret,
        "machine_name": machine_name,
        "bot_url": bot_url,
    }

    # Override logging settings from config.json if file exists
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = json.load(f)

        logging_cfg = data.get("logging", {})
        if "level" in logging_cfg:
            kwargs["log_level"] = logging_cfg["level"]
        if "file" in logging_cfg:
            kwargs["log_file"] = logging_cfg["file"]
        if "rotation" in logging_cfg:
            kwargs["log_rotation"] = logging_cfg["rotation"]
        if "retention" in logging_cfg:
            kwargs["log_retention"] = logging_cfg["retention"]

    return AgentConfig(**kwargs)
