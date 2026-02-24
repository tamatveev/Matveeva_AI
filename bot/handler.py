import logging

from aiogram import Dispatcher, types
from aiogram.filters import CommandStart

logger = logging.getLogger(__name__)

GREETING = "Привет! Я бот-ассистент. Напишите мне что-нибудь, и я отвечу."


class Handler:
    def register(self, dp: Dispatcher) -> None:
        dp.message.register(self._on_start, CommandStart())
        dp.message.register(self._on_message)

    async def _on_start(self, message: types.Message) -> None:
        logger.info("chat_id=%s — /start", message.chat.id)
        await message.answer(GREETING)

    async def _on_message(self, message: types.Message) -> None:
        if not message.text:
            return
        logger.info("chat_id=%s — сообщение: %s", message.chat.id, message.text[:50])
        await message.answer(message.text)
