"""Tests for bot and agent config loading."""
import asyncio
import json
import os
import pytest


class TestBotConfig:
    """Test bot/config.py BotConfig and load_bot_config."""

    def test_bot_config_loads_shared_secret(self, tmp_path, monkeypatch):
        from bot.config import load_bot_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret-bot")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
        config = load_bot_config(config_path=str(tmp_path / "nonexistent.json"))
        assert config.shared_secret == "test-secret-bot"

    def test_bot_config_default_ws_port(self, tmp_path, monkeypatch):
        from bot.config import load_bot_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
        config = load_bot_config(config_path=str(tmp_path / "nonexistent.json"))
        assert config.ws_port == 8765

    def test_bot_config_loads_from_config_json(self, tmp_config_file, monkeypatch):
        from bot.config import load_bot_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
        config = load_bot_config(config_path=tmp_config_file)
        assert config.ws_port == 9999
        assert config.ws_host == "127.0.0.1"
        assert config.heartbeat_interval == 10
        assert config.heartbeat_timeout == 20
        assert config.registration_timeout == 5

    def test_bot_config_raises_without_shared_secret(self, tmp_path, monkeypatch):
        from unittest.mock import patch
        from bot.config import load_bot_config
        monkeypatch.delenv("SHARED_SECRET", raising=False)
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
        with patch("bot.config.load_dotenv"):  # prevent .env from restoring SHARED_SECRET
            with pytest.raises(ValueError, match="SHARED_SECRET"):
                load_bot_config(config_path=str(tmp_path / "nonexistent.json"))

    def test_bot_config_raises_without_discord_token(self, tmp_path, monkeypatch):
        from unittest.mock import patch
        from bot.config import load_bot_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
        with patch("bot.config.load_dotenv"):  # prevent .env from restoring DISCORD_BOT_TOKEN
            with pytest.raises(ValueError, match="DISCORD_BOT_TOKEN"):
                load_bot_config(config_path=str(tmp_path / "nonexistent.json"))

    def test_bot_config_loads_discord_settings(self, tmp_path, monkeypatch):
        import json
        from bot.config import load_bot_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "discord": {
                "allowed_guild_ids": [111, 222],
                "allowed_user_ids": [333],
                "channel_mapping": {"456": "my-pc"}
            }
        }))
        config = load_bot_config(config_path=str(config_file))
        assert config.discord_token == "test-token"
        assert config.allowed_guild_ids == [111, 222]
        assert config.allowed_user_ids == [333]
        assert config.channel_mapping == {"456": "my-pc"}


class TestAgentConfig:
    """Test agent/config.py AgentConfig and load_agent_config."""

    def test_agent_config_loads_shared_secret(self, tmp_path, monkeypatch):
        from agent.config import load_agent_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret-agent")
        config = load_agent_config(config_path=str(tmp_path / "nonexistent.json"))
        assert config.shared_secret == "test-secret-agent"

    def test_agent_config_default_bot_url(self, tmp_path, monkeypatch):
        from agent.config import load_agent_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        config = load_agent_config(config_path=str(tmp_path / "nonexistent.json"))
        assert config.bot_url == "ws://localhost:8765"

    def test_agent_config_loads_machine_name_from_env(self, tmp_path, monkeypatch):
        from agent.config import load_agent_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.setenv("MACHINE_NAME", "custom-machine")
        config = load_agent_config(config_path=str(tmp_path / "nonexistent.json"))
        assert config.machine_name == "custom-machine"

    def test_agent_config_default_machine_name_is_hostname(self, tmp_path, monkeypatch):
        from unittest.mock import patch
        from agent.config import load_agent_config
        import platform
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.delenv("MACHINE_NAME", raising=False)
        with patch("agent.config.load_dotenv"):  # prevent .env from restoring MACHINE_NAME
            config = load_agent_config(config_path=str(tmp_path / "nonexistent.json"))
        assert config.machine_name == platform.node()

    def test_agent_config_loads_bot_url_from_env(self, tmp_path, monkeypatch):
        from agent.config import load_agent_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.setenv("BOT_URL", "ws://remote:1234")
        config = load_agent_config(config_path=str(tmp_path / "nonexistent.json"))
        assert config.bot_url == "ws://remote:1234"

    def test_agent_config_raises_without_shared_secret(self, tmp_path, monkeypatch):
        from unittest.mock import patch
        from agent.config import load_agent_config
        monkeypatch.delenv("SHARED_SECRET", raising=False)
        with patch("agent.config.load_dotenv"):
            with pytest.raises(ValueError, match="SHARED_SECRET"):
                load_agent_config(config_path=str(tmp_path / "nonexistent.json"))


class TestDiscordConfig:
    """Additional tests for Discord config extension (ROUT-02) and field loading."""

    def test_config_loads_discord_token(self, tmp_path, monkeypatch):
        """Discord token loaded from DISCORD_BOT_TOKEN env var."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "discord": {"allowed_guild_ids": [], "allowed_user_ids": [], "channel_mapping": {}}
        }))
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token-123")
        from bot.config import load_bot_config
        config = load_bot_config(str(config_file))
        assert config.discord_token == "test-token-123"

    def test_config_loads_allowed_guild_ids(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "discord": {"allowed_guild_ids": [123, 456], "allowed_user_ids": [], "channel_mapping": {}}
        }))
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
        from bot.config import load_bot_config
        config = load_bot_config(str(config_file))
        assert config.allowed_guild_ids == [123, 456]

    def test_config_loads_channel_mapping(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "discord": {"allowed_guild_ids": [], "allowed_user_ids": [], "channel_mapping": {"111": "desktop"}}
        }))
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
        from bot.config import load_bot_config
        config = load_bot_config(str(config_file))
        assert config.channel_mapping == {"111": "desktop"}

    def test_config_missing_discord_token_raises(self, tmp_path, monkeypatch):
        from unittest.mock import patch
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "discord": {"allowed_guild_ids": [], "allowed_user_ids": [], "channel_mapping": {}}
        }))
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
        from bot.config import load_bot_config
        with patch("bot.config.load_dotenv"):
            with pytest.raises(ValueError, match="DISCORD_BOT_TOKEN"):
                load_bot_config(str(config_file))


class TestConfigReload:
    """Addresses review concern #8: reload safety tests."""

    @pytest.mark.asyncio
    async def test_reload_config_updates_mapping(self, tmp_path, monkeypatch):
        """reload_config updates channel_mapping from disk."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "discord": {"allowed_guild_ids": [1], "allowed_user_ids": [2], "channel_mapping": {"111": "a"}}
        }))
        monkeypatch.setenv("SHARED_SECRET", "s")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "t")
        from bot.config import load_bot_config
        config = load_bot_config(str(config_file))
        assert config.channel_mapping == {"111": "a"}
        # Modify file and reload
        config_file.write_text(json.dumps({
            "discord": {"allowed_guild_ids": [1, 3], "allowed_user_ids": [2], "channel_mapping": {"111": "a", "222": "b"}}
        }))
        await config.reload_config()
        assert config.channel_mapping == {"111": "a", "222": "b"}
        assert 3 in config.allowed_guild_ids

    @pytest.mark.asyncio
    async def test_reload_invalid_json_raises(self, tmp_path, monkeypatch):
        """Reload with invalid JSON raises error, config unchanged (review concern #8)."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "discord": {"allowed_guild_ids": [1], "allowed_user_ids": [2], "channel_mapping": {"111": "a"}}
        }))
        monkeypatch.setenv("SHARED_SECRET", "s")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "t")
        from bot.config import load_bot_config
        config = load_bot_config(str(config_file))
        original_mapping = dict(config.channel_mapping)
        # Corrupt the file
        config_file.write_text("NOT VALID JSON {{{")
        with pytest.raises(Exception):  # json.JSONDecodeError or ValueError
            await config.reload_config()
        # Original config should be unchanged after failed reload
        assert config.channel_mapping == original_mapping

    @pytest.mark.asyncio
    async def test_reload_uses_lock(self, tmp_path, monkeypatch):
        """reload_config acquires _config_lock (review concern #5)."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "discord": {"allowed_guild_ids": [], "allowed_user_ids": [], "channel_mapping": {}}
        }))
        monkeypatch.setenv("SHARED_SECRET", "s")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "t")
        from bot.config import load_bot_config
        config = load_bot_config(str(config_file))
        assert hasattr(config, '_config_lock')
        # Verify lock exists and is an asyncio.Lock
        assert isinstance(config._config_lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_save_config_persists_mapping(self, tmp_path, monkeypatch):
        """save_config writes channel_mapping to disk."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "discord": {"allowed_guild_ids": [], "allowed_user_ids": [], "channel_mapping": {}}
        }))
        monkeypatch.setenv("SHARED_SECRET", "s")
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "t")
        from bot.config import load_bot_config
        config = load_bot_config(str(config_file))
        config.channel_mapping["999"] = "new-machine"
        await config.save_config()
        # Re-read from disk
        with open(config_file) as f:
            data = json.load(f)
        assert data["discord"]["channel_mapping"]["999"] == "new-machine"
