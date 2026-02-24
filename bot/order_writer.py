import logging
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from bot.config import Config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


class OrderWriter:
    def __init__(self, config: Config) -> None:
        creds = Credentials.from_service_account_file(
            str(config.service_account_path), scopes=SCOPES,
        )
        gc = gspread.authorize(creds)
        sheet = gc.open_by_url(config.google_sheets_orders_url)
        self._worksheet = sheet.sheet1

    def write(
        self, client_name: str, email: str, service: str,
        comment: str, telegram_id: str, chat_id: int,
    ) -> None:
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            client_name,
            email,
            telegram_id,
            str(chat_id),
            service,
            comment,
        ]
        next_row = len(self._worksheet.get_all_values()) + 1
        self._worksheet.update(f"A{next_row}", [row])
        logger.info("Заявка записана: %s — %s", client_name, service)
