import logging
import re
import uuid

from aiogram import Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)

from bot.config import Config
from bot.llm_client import LLMClient
from bot.order_writer import OrderWriter
from bot.prompt import Prompt
from bot.sheets_client import SheetsClient

logger = logging.getLogger(__name__)

GREETING = """Привет!

Это умный бот нейро-креатора Анастасии Матвеевой.
Здесь можно ознакомиться со всеми услугами, ценами или обсудить свой уникальный проект."""

_BUTTONS_RE = re.compile(r"\[buttons]\s*\n(.*?)\n\s*\[/buttons]", re.DOTALL)
_ORDER_RE = re.compile(r"\[order]\s*\n(.*?)\n\s*\[/order]", re.DOTALL)
_EXAMPLE_PREFIX = "example:"
_BEST_EXAMPLE = "best_example"


class Handler:
    def __init__(
        self, config: Config, llm_client: LLMClient,
        prompt: Prompt, sheets_client: SheetsClient,
        order_writer: OrderWriter,
    ) -> None:
        self._llm_client = llm_client
        self._prompt = prompt
        self._sheets_client = sheets_client
        self._order_writer = order_writer
        self._notify_chat_id = config.telegram_notify_chat_id
        self._best_example_url = config.best_example_url
        self._greeting_image_url = config.greeting_image_url
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

        greeting_photo: bytes | None = None
        if self._greeting_image_url:
            _, images = self._sheets_client.download_examples(self._greeting_image_url)
            if images:
                greeting_photo = images[0]

        await self._handle_user_text(
            chat_id, "Начать", message, first_message_photo=greeting_photo,
        )

    async def _on_message(self, message: types.Message) -> None:
        if not message.text:
            return
        await self._handle_user_text(message.chat.id, message.text, message)

    async def _on_callback(self, callback: types.CallbackQuery) -> None:
        if not callback.data or not callback.message:
            return
        raw = self._button_map.pop(callback.data, callback.data)
        chat_id = callback.message.chat.id
        await callback.answer()

        if raw == _BEST_EXAMPLE:
            logger.info("chat_id=%s — запрос лучшего примера", chat_id)
            await callback.message.answer("👆 Примеры работ")
            await self._send_examples(callback.message, self._best_example_url)
            return

        if raw.startswith(_EXAMPLE_PREFIX):
            drive_url = raw[len(_EXAMPLE_PREFIX):]
            logger.info("chat_id=%s — запрос примера по услуге", chat_id)
            await callback.message.answer("👆 Показать пример")
            await self._send_examples(callback.message, drive_url)
            return

        logger.info("chat_id=%s — кнопка: %s", chat_id, raw)
        await callback.message.answer(f"👆 {raw}")
        await self._handle_user_text(chat_id, raw, callback.message)

    async def _handle_user_text(
        self,
        chat_id: int,
        text: str,
        target: types.Message,
        *,
        first_message_photo: bytes | None = None,
    ) -> None:
        logger.info("chat_id=%s — сообщение: %s", chat_id, text[:50])

        history = self._histories.setdefault(chat_id, [])
        history.append({"role": "user", "content": text})

        messages = self._prompt.build(history)
        answer = await self._llm_client.complete(messages)

        history.append({"role": "assistant", "content": answer})
        self._trim_history(chat_id)

        await self._try_save_order(answer, target)
        clean_answer = _ORDER_RE.sub("", answer).strip()
        body, keyboard = self._parse_buttons(clean_answer, text)

        if first_message_photo is not None:
            photo = BufferedInputFile(first_message_photo, filename="greeting.jpg")
            await target.answer_photo(photo, caption=body, reply_markup=keyboard)
        else:
            await target.answer(body, reply_markup=keyboard)

    def _parse_buttons(
        self, text: str, user_text: str,
    ) -> tuple[str, InlineKeyboardMarkup | None]:
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
            label_lower = label.lower().strip()
            if label_lower in ("примеры работ", "посмотреть примеры работ"):
                self._button_map[key] = _BEST_EXAMPLE
                buttons.append([InlineKeyboardButton(text=f"📸 {label}", callback_data=key)])
            elif label_lower == "показать пример":
                url = self._sheets_client.find_example_url(user_text)
                if url:
                    self._button_map[key] = f"{_EXAMPLE_PREFIX}{url}"
                    buttons.append([
                        InlineKeyboardButton(text="📸 Показать пример", callback_data=key),
                    ])
                else:
                    self._button_map[key] = label
                    buttons.append([InlineKeyboardButton(text=label, callback_data=key)])
            else:
                self._button_map[key] = label
                buttons.append([InlineKeyboardButton(text=label, callback_data=key)])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        return body or text, keyboard

    async def _try_save_order(self, answer: str, target: types.Message) -> None:
        match = _ORDER_RE.search(answer)
        if not match:
            return

        fields: dict[str, str] = {}
        for line in match.group(1).splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                fields[key.strip().lower()] = value.strip()

        client_name = fields.get("имя", "")
        service = fields.get("услуга", "")
        email = fields.get("почта", "")
        comment = fields.get("комментарий", "")
        telegram_id = target.chat.username or ""
        chat_id = target.chat.id

        try:
            self._order_writer.write(client_name, email, service, comment, telegram_id, chat_id)
            logger.info("chat_id=%s — заявка сохранена", target.chat.id)
        except Exception:
            logger.exception("chat_id=%s — ошибка записи заявки", target.chat.id)
            await target.answer("Произошла ошибка при сохранении заявки. Попробуйте позже.")
            return

        # Уведомления: только логируем ошибки, не показываем пользователю
        if self._notify_chat_id:
            try:
                text = (
                    f"Новая заявка\n\n"
                    f"Имя: {client_name}\n"
                    f"Почта: {email}\n"
                    f"Услуга: {service}\n"
                    f"Комментарий: {comment or '—'}\n"
                    f"Telegram: @{telegram_id or '—'} (chat_id: {chat_id})"
                )
                await target.bot.send_message(self._notify_chat_id, text)
            except Exception:
                logger.exception("chat_id=%s — ошибка отправки уведомления в Telegram", target.chat.id)

    async def _send_examples(self, target: types.Message, drive_url: str) -> None:
        raw_description, images = self._sheets_client.download_examples(drive_url)
        if not raw_description and not images:
            await target.answer("К сожалению, не удалось загрузить примеры.")
            return
        caption_text: str | None = None
        caption_keyboard: InlineKeyboardMarkup | None = None
        if raw_description and images:
            caption_raw = await self._caption_from_description(target.chat.id, raw_description)
            if caption_raw:
                history = self._histories.get(target.chat.id, [])
                last_user = next(
                    (m["content"] for m in reversed(history) if m["role"] == "user"),
                    "",
                )
                caption_text, caption_keyboard = self._parse_buttons(caption_raw, last_user)
                caption_text = caption_text.strip() or None
            if not caption_text:
                caption_text = raw_description.strip() or None
        elif raw_description and not images:
            await target.answer(raw_description)
            return
        if len(images) == 1:
            photo = BufferedInputFile(images[0], filename="example.jpg")
            await target.answer_photo(
                photo, caption=caption_text, reply_markup=caption_keyboard
            )
            return
        media = [
            InputMediaPhoto(
                media=BufferedInputFile(data, filename=f"example_{i}.jpg"),
                caption=caption_text if i == 0 else None,
            )
            for i, data in enumerate(images)
        ]
        await target.answer_media_group(media)
        if caption_keyboard:
            await target.answer("Что делаем дальше?", reply_markup=caption_keyboard)

    async def _caption_from_description(self, chat_id: int, description: str) -> str | None:
        """Подпись к примерам: тот же запрос к LLM, что и в диалоге (системный промпт + история), плюс описание примера из Google Doc."""
        history = self._histories.get(chat_id, [])
        messages = self._prompt.build(history)
        messages.append({"role": "user", "content": description.strip()})
        try:
            text = await self._llm_client.complete(messages)
            return text.strip() if text else None
        except Exception:
            logger.exception("Ошибка генерации подписи к примеру")
            return None

    def _trim_history(self, chat_id: int) -> None:
        history = self._histories.get(chat_id)
        if history and len(history) > self._max_history:
            self._histories[chat_id] = history[-self._max_history:]
