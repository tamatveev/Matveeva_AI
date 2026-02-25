import logging
import os
import tempfile
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
        self.google_sheets_orders_url: str = self._require("GOOGLE_SHEETS_ORDERS_URL")
        self.best_example_url: str = self._require("BEST_EXAMPLE_URL")
        self.service_account_path: Path = self._resolve_service_account_path()
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

        # Уведомление о заявке в Telegram (опционально)
        self.telegram_notify_chat_id: int | None = self._optional_int("TELEGRAM_NOTIFY_CHAT_ID")

    def _resolve_service_account_path(self) -> Path:
        """Путь к ключу: из файла (GOOGLE_APPLICATION_CREDENTIALS) или из JSON в переменной (для Railway)."""
        json_content = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if json_content:
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            )
            tmp.write(json_content)
            tmp.close()
            logger.info("Ключ Google взят из переменной GOOGLE_SERVICE_ACCOUNT_JSON")
            return Path(tmp.name)
        return Path(self._require("GOOGLE_APPLICATION_CREDENTIALS"))

    @staticmethod
    def _require(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"Переменная окружения {name} не задана")
        return value

    @staticmethod
    def _optional_int(name: str) -> int | None:
        value = os.getenv(name)
        if not value:
            return None
        try:
            return int(value.strip())
        except ValueError:
            return None

    def setup_logging(self) -> None:
        logging.basicConfig(
            level=self.log_level,
            format="%(asctime)s — %(levelname)s — %(name)s — %(message)s",
        )
        logger.info("Логгирование настроено, уровень: %s", self.log_level)
