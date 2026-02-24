import asyncio

from bot.bot import Bot
from bot.config import Config


def main() -> None:
    config = Config()
    config.setup_logging()

    bot = Bot(config)
    asyncio.run(bot.start())


if __name__ == "__main__":
    main()
