"""Tests for bot and agent config loading."""
import os
import pytest


class TestBotConfig:
    """Test bot/config.py BotConfig and load_bot_config."""

    def test_bot_config_loads_shared_secret(self, tmp_path, monkeypatch):
        from bot.config import load_bot_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret-bot")
        config = load_bot_config(config_path=str(tmp_path / "nonexistent.json"))
        assert config.shared_secret == "test-secret-bot"

    def test_bot_config_default_ws_port(self, tmp_path, monkeypatch):
        from bot.config import load_bot_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        config = load_bot_config(config_path=str(tmp_path / "nonexistent.json"))
        assert config.ws_port == 8765

    def test_bot_config_loads_from_config_json(self, tmp_config_file, monkeypatch):
        from bot.config import load_bot_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        config = load_bot_config(config_path=tmp_config_file)
        assert config.ws_port == 9999
        assert config.ws_host == "127.0.0.1"
        assert config.heartbeat_interval == 10
        assert config.heartbeat_timeout == 20
        assert config.registration_timeout == 5

    def test_bot_config_raises_without_shared_secret(self, tmp_path, monkeypatch):
        from bot.config import load_bot_config
        monkeypatch.delenv("SHARED_SECRET", raising=False)
        with pytest.raises(ValueError, match="SHARED_SECRET"):
            load_bot_config(config_path=str(tmp_path / "nonexistent.json"))


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
        from agent.config import load_agent_config
        import platform
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.delenv("MACHINE_NAME", raising=False)
        config = load_agent_config(config_path=str(tmp_path / "nonexistent.json"))
        assert config.machine_name == platform.node()

    def test_agent_config_loads_bot_url_from_env(self, tmp_path, monkeypatch):
        from agent.config import load_agent_config
        monkeypatch.setenv("SHARED_SECRET", "test-secret")
        monkeypatch.setenv("BOT_URL", "ws://remote:1234")
        config = load_agent_config(config_path=str(tmp_path / "nonexistent.json"))
        assert config.bot_url == "ws://remote:1234"

    def test_agent_config_raises_without_shared_secret(self, tmp_path, monkeypatch):
        from agent.config import load_agent_config
        monkeypatch.delenv("SHARED_SECRET", raising=False)
        with pytest.raises(ValueError, match="SHARED_SECRET"):
            load_agent_config(config_path=str(tmp_path / "nonexistent.json"))
