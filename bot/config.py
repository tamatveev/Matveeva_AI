import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class Config:
    def __init__(self) -> None:
        load_dotenv(_ENV_PATH)

        self.telegram_bot_token: str = self._require("TELEGRAM_BOT_TOKEN")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @staticmethod
    def _require(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"Переменная окружения {name} не задана")
        return value

    def setup_logging(self) -> None:
        logging.basicConfig(
            level=self.log_level,
            format="%(asctime)s — %(levelname)s — %(name)s — %(message)s",
        )
        logger.info("Логгирование настроено, уровень: %s", self.log_level)
