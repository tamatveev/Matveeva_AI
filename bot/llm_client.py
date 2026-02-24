import logging

from openai import AsyncOpenAI

from bot.config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config: Config) -> None:
        self._client = AsyncOpenAI(
            api_key=config.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self._model = config.llm_model

    async def complete(self, messages: list[dict[str, str]]) -> str:
        logger.info("Запрос к LLM, сообщений: %d", len(messages))
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        text = response.choices[0].message.content or ""
        logger.info("Ответ LLM получен, длина: %d", len(text))
        return text
