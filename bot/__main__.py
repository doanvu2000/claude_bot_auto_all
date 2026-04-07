"""Entry point: python -m bot"""
import asyncio

import discord
from loguru import logger
from websockets.asyncio.server import serve

from bot.config import load_bot_config
from bot.discord_bot import TerminalBot
from bot.server import AgentManager


async def run() -> None:
    """Start WebSocket server and Discord bot on the same event loop.

    Startup order (D-02): WS server starts first so agents can connect
    immediately, then Discord bot connects.

    Shutdown (D-03): On any exit, gracefully cancel heartbeat, close WS
    server, and close Discord bot.
    """
    config = load_bot_config()

    manager = AgentManager(config)

    # D-02: WS server starts first (agents can connect immediately)
    ws_server = await serve(manager.handler, config.ws_host, config.ws_port)
    logger.info(f"WebSocket server started on ws://{config.ws_host}:{config.ws_port}")

    heartbeat_task = asyncio.create_task(manager._heartbeat_loop())

    bot = TerminalBot(agent_manager=manager, config=config)
    bot.setup_agent_callbacks()

    try:
        # Addresses review concern #7: if Discord login fails, we shut down cleanly
        # rather than leaving WS server running in degraded mode.
        await bot.start(config.discord_token)
    except discord.LoginFailure as e:
        logger.error(f"Discord login failed: {e}. Check DISCORD_BOT_TOKEN in bot/.env")
        # Startup failure policy: exit process. Do NOT run degraded transport-only mode.
        # Rationale: bot without Discord is useless for this project's purpose.
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        # D-03: graceful shutdown of both systems
        logger.info("Shutting down...")
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        ws_server.close()
        await ws_server.wait_closed()
        if not bot.is_closed():
            await bot.close()
        logger.info("Shutdown complete")


def main() -> None:
    """Run the bot."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
