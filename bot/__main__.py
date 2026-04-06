"""Entry point: python -m bot"""
import asyncio

from loguru import logger

from bot.config import load_bot_config
from bot.server import start_server


def main():
    config = load_bot_config()
    logger.info(f"Starting bot WebSocket server on ws://{config.ws_host}:{config.ws_port}")
    asyncio.run(start_server(config))


if __name__ == "__main__":
    main()
