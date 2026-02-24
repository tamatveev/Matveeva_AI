import logging

from bot.config import Config

logger = logging.getLogger(__name__)

BUTTONS_INSTRUCTION = """
Когда предлагаешь варианты действий, оформляй их в виде кнопок в специальном формате:

[buttons]
Вариант 1
Вариант 2
Вариант 3
[/buttons]

Кнопки ставь в конце сообщения после основного текста. Всегда предлагай кнопки, чтобы пользователю было удобно выбирать.
""".strip()


class Prompt:
    def __init__(self, config: Config) -> None:
        self._system_prompt = config.system_prompt

    def build(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        full_system = f"{self._system_prompt}\n\n{BUTTONS_INSTRUCTION}"
        return [{"role": "system", "content": full_system}, *history]
