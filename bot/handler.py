import logging

from aiogram import Dispatcher, types
from aiogram.filters import CommandStart

from bot.config import Config
from bot.llm_client import LLMClient
from bot.prompt import Prompt

logger = logging.getLogger(__name__)

GREETING = "Привет! Я бот-ассистент. Чем могу помочь?"


class Handler:
    def __init__(self, config: Config, llm_client: LLMClient, prompt: Prompt) -> None:
        self._llm_client = llm_client
        self._prompt = prompt
        self._max_history = config.max_history_messages
        self._histories: dict[int, list[dict[str, str]]] = {}

    def register(self, dp: Dispatcher) -> None:
        dp.message.register(self._on_start, CommandStart())
        dp.message.register(self._on_message)

    async def _on_start(self, message: types.Message) -> None:
        chat_id = message.chat.id
        logger.info("chat_id=%s — /start", chat_id)
        self._histories.pop(chat_id, None)
        await message.answer(GREETING)

    async def _on_message(self, message: types.Message) -> None:
        if not message.text:
            return

        chat_id = message.chat.id
        text = message.text
        logger.info("chat_id=%s — сообщение: %s", chat_id, text[:50])

        history = self._histories.setdefault(chat_id, [])
        history.append({"role": "user", "content": text})

        messages = self._prompt.build(history)
        answer = await self._llm_client.complete(messages)

        history.append({"role": "assistant", "content": answer})

        self._trim_history(chat_id)

        await message.answer(answer)

    def _trim_history(self, chat_id: int) -> None:
        history = self._histories.get(chat_id)
        if history and len(history) > self._max_history:
            self._histories[chat_id] = history[-self._max_history:]
