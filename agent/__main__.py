"""Entry point: python -m agent"""
from agent.config import load_agent_config


def main():
    config = load_agent_config()
    print(f"Agent config loaded: connecting to {config.bot_url}")
    # Client implementation added in Plan 03


if __name__ == "__main__":
    main()
