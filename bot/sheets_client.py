import logging
import re

import gspread
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

from bot.config import Config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

_DOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")


class SheetsClient:
    def __init__(self, config: Config) -> None:
        creds = Credentials.from_service_account_file(
            str(config.service_account_path), scopes=SCOPES,
        )
        self._gc = gspread.authorize(creds)
        self._authed_session = AuthorizedSession(creds)
        self._services_url = config.google_sheets_services_url
        self._prompt_doc_url = config.google_doc_prompt_url
        self.services: list[dict[str, str]] = []

    def load_services(self) -> None:
        logger.info("Загрузка услуг из Google Sheets...")
        sheet = self._gc.open_by_url(self._services_url)
        worksheet = sheet.sheet1
        rows = worksheet.get_all_records()
        self.services = [dict(row) for row in rows]
        logger.info("Загружено услуг: %d", len(self.services))

    def format_services_for_prompt(self) -> str:
        if not self.services:
            return "Список услуг пока пуст."

        lines: list[str] = []
        for s in self.services:
            parts = [f"— {s.get('Название', '?')}"]
            if desc := s.get("Описание"):
                parts.append(f"  Описание: {desc}")
            if price := s.get("Цена"):
                parts.append(f"  Цена: {price}")
            if deadline := s.get("Сроки"):
                parts.append(f"  Сроки: {deadline}")
            lines.append("\n".join(parts))

        return "Перечень услуг:\n\n" + "\n\n".join(lines)

    def load_prompt(self) -> str:
        logger.info("Загрузка системного промта из Google Doc...")
        match = _DOC_ID_RE.search(self._prompt_doc_url)
        if not match:
            raise RuntimeError(f"Не удалось извлечь ID документа из URL: {self._prompt_doc_url}")

        doc_id = match.group(1)
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        response = self._authed_session.get(export_url)
        response.raise_for_status()

        text = response.text.strip()
        logger.info("Системный промт загружен, длина: %d символов", len(text))
        return text
