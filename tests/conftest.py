"""Shared test fixtures."""
import os
import json
import tempfile
import pytest


@pytest.fixture
def tmp_env_file(tmp_path):
    """Create a temporary .env file with test values."""
    env_file = tmp_path / ".env"
    env_file.write_text("SHARED_SECRET=test-secret-123\nMACHINE_NAME=test-machine\nBOT_URL=ws://localhost:9999\n")
    return str(env_file)


@pytest.fixture
def tmp_config_file(tmp_path):
    """Create a temporary config.json with test values."""
    config = {
        "websocket": {
            "host": "127.0.0.1",
            "port": 9999
        },
        "heartbeat": {
            "interval_seconds": 10,
            "timeout_seconds": 20
        },
        "auth": {
            "registration_timeout_seconds": 5
        },
        "logging": {
            "level": "DEBUG",
            "file": "logs/test.log",
            "rotation": "5 MB",
            "retention": "3 days"
        }
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    return str(config_file)
