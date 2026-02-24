import logging

from aiogram import Bot as AiogramBot, Dispatcher

from bot.config import Config
from bot.handler import Handler

logger = logging.getLogger(__name__)


class Bot:
    def __init__(self, config: Config) -> None:
        self._bot = AiogramBot(token=config.telegram_bot_token)
        self._dp = Dispatcher()
        self._handler = Handler()
        self._handler.register(self._dp)

    async def start(self) -> None:
        logger.info("Бот запускается...")
        try:
            await self._dp.start_polling(self._bot)
        finally:
            await self._bot.session.close()
            logger.info("Бот остановлен")
