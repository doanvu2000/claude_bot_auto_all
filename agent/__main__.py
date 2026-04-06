"""Entry point: python -m agent"""
import asyncio
import signal

from loguru import logger

from agent.client import AgentClient
from agent.config import load_agent_config


def main():
    config = load_agent_config()
    client = AgentClient(config)

    shutdown_event = asyncio.Event()

    def _signal_handler(*_):
        shutdown_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    async def run():
        agent_task = asyncio.create_task(client.run())
        await shutdown_event.wait()
        await client.stop()
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass

    logger.info(f"Agent starting: {config.machine_name} -> {config.bot_url}")
    asyncio.run(run())


if __name__ == "__main__":
    main()
