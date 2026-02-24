import logging

from bot.config import Config

logger = logging.getLogger(__name__)


class Prompt:
    def __init__(self, config: Config) -> None:
        self._system_prompt = config.system_prompt

    def build(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        return [{"role": "system", "content": self._system_prompt}, *history]
