"""Entry point: python -m bot"""
from bot.config import load_bot_config


def main():
    config = load_bot_config()
    print(f"Bot config loaded: ws://{config.ws_host}:{config.ws_port}")
    # Server implementation added in Plan 02


if __name__ == "__main__":
    main()
