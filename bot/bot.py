import logging

from aiogram import Bot as AiogramBot, Dispatcher

from bot.config import Config
from bot.handler import Handler
from bot.llm_client import LLMClient
from bot.order_writer import OrderWriter
from bot.prompt import Prompt
from bot.sheets_client import SheetsClient

logger = logging.getLogger(__name__)


class Bot:
    def __init__(self, config: Config) -> None:
        self._bot = AiogramBot(token=config.telegram_bot_token)
        self._dp = Dispatcher()

        sheets_client = SheetsClient(config)
        sheets_client.load_services()
        system_prompt = sheets_client.load_prompt()

        llm_client = LLMClient(config)
        services_text = sheets_client.format_services_for_prompt()
        prompt = Prompt(system_prompt, services_text)
        self._sheets_client = sheets_client

        order_writer = OrderWriter(config)
        handler = Handler(config, llm_client, prompt, sheets_client, order_writer)
        handler.register(self._dp)

    async def start(self) -> None:
        logger.info("Бот запускается...")
        try:
            await self._dp.start_polling(self._bot)
        finally:
            await self._bot.session.close()
            logger.info("Бот остановлен")
