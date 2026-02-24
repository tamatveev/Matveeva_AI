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
        self.openrouter_api_key: str = self._require("OPENROUTER_API_KEY")
        self.llm_model: str = self._require("LLM_MODEL")
        self.max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))
        self.google_sheets_services_url: str = self._require("GOOGLE_SHEETS_SERVICES_URL")
        self.google_doc_prompt_url: str = self._require("GOOGLE_DOC_PROMPT_URL")
        self.service_account_path: Path = Path(self._require("GOOGLE_APPLICATION_CREDENTIALS"))
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
