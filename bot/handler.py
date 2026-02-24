import logging
import re
import uuid

from aiogram import Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import Config
from bot.llm_client import LLMClient
from bot.prompt import Prompt

logger = logging.getLogger(__name__)

GREETING = "Привет! Я бот-ассистент. Чем могу помочь?"

_BUTTONS_RE = re.compile(r"\[buttons]\s*\n(.*?)\n\s*\[/buttons]", re.DOTALL)


class Handler:
    def __init__(self, config: Config, llm_client: LLMClient, prompt: Prompt) -> None:
        self._llm_client = llm_client
        self._prompt = prompt
        self._max_history = config.max_history_messages
        self._histories: dict[int, list[dict[str, str]]] = {}
        self._button_map: dict[str, str] = {}

    def register(self, dp: Dispatcher) -> None:
        dp.message.register(self._on_start, CommandStart())
        dp.message.register(self._on_message)
        dp.callback_query.register(self._on_callback)

    async def _on_start(self, message: types.Message) -> None:
        chat_id = message.chat.id
        logger.info("chat_id=%s — /start", chat_id)
        self._histories.pop(chat_id, None)
        await message.answer(GREETING)

    async def _on_message(self, message: types.Message) -> None:
        if not message.text:
            return
        await self._handle_user_text(message.chat.id, message.text, message)

    async def _on_callback(self, callback: types.CallbackQuery) -> None:
        if not callback.data or not callback.message:
            return
        text = self._button_map.pop(callback.data, callback.data)
        chat_id = callback.message.chat.id
        logger.info("chat_id=%s — кнопка: %s", chat_id, text)
        await callback.answer()
        await callback.message.answer(f"👆 {text}")
        await self._handle_user_text(chat_id, text, callback.message)

    async def _handle_user_text(
        self, chat_id: int, text: str, target: types.Message,
    ) -> None:
        logger.info("chat_id=%s — сообщение: %s", chat_id, text[:50])

        history = self._histories.setdefault(chat_id, [])
        history.append({"role": "user", "content": text})

        messages = self._prompt.build(history)
        answer = await self._llm_client.complete(messages)

        history.append({"role": "assistant", "content": answer})
        self._trim_history(chat_id)

        body, buttons = self._parse_buttons(answer)
        await target.answer(body, reply_markup=buttons)

    def _parse_buttons(self, text: str) -> tuple[str, InlineKeyboardMarkup | None]:
        match = _BUTTONS_RE.search(text)
        if not match:
            return text, None

        body = text[: match.start()].strip()
        lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
        if not lines:
            return body or text, None

        buttons: list[list[InlineKeyboardButton]] = []
        for label in lines:
            key = uuid.uuid4().hex[:12]
            self._button_map[key] = label
            buttons.append([InlineKeyboardButton(text=label, callback_data=key)])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        return body or text, keyboard

    def _trim_history(self, chat_id: int) -> None:
        history = self._histories.get(chat_id)
        if history and len(history) > self._max_history:
            self._histories[chat_id] = history[-self._max_history:]
