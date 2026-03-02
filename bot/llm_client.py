import logging

from openai import AsyncOpenAI

from bot.config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config: Config) -> None:
        if config.openai_api_key:
            self._client = AsyncOpenAI(api_key=config.openai_api_key)
            logger.info("LLM: OpenAI (напрямую), модель %s", config.llm_model)
        else:
            self._client = AsyncOpenAI(
                api_key=config.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
            )
            logger.info("LLM: OpenRouter, модель %s", config.llm_model)
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
