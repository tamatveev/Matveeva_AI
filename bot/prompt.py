import logging

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
    def __init__(self, system_prompt: str, services_text: str = "") -> None:
        self._system_prompt = system_prompt
        self._services_text = services_text

    def build(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        parts = [self._system_prompt]
        if self._services_text:
            parts.append(self._services_text)
        parts.append(BUTTONS_INSTRUCTION)
        full_system = "\n\n".join(parts)
        return [{"role": "system", "content": full_system}, *history]
