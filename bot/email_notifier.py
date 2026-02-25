import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from bot.config import Config

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Отправка уведомления по почте при сохранении заявки."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._enabled = bool(
            config.smtp_host
            and config.smtp_port
            and config.smtp_user
            and config.smtp_password
            and config.notify_email
        )

    def notify(
        self,
        client_name: str,
        email: str,
        service: str,
        comment: str,
    ) -> None:
        """Отправить письмо о новой заявке. При ошибке только логируем."""
        if not self._enabled:
            return

        subject = "Новая заявка с сайта"
        body = (
            f"Поступила новая заявка.\n\n"
            f"Имя: {client_name}\n"
            f"Почта клиента: {email}\n"
            f"Услуга: {service}\n"
            f"Комментарий: {comment or '—'}\n"
        )

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self._config.smtp_user
            msg["To"] = self._config.notify_email
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(
                self._config.smtp_host, self._config.smtp_port
            ) as server:
                server.starttls()
                server.login(self._config.smtp_user, self._config.smtp_password)
                server.sendmail(
                    self._config.smtp_user,
                    self._config.notify_email,
                    msg.as_string(),
                )
            logger.info("Уведомление о заявке отправлено на %s", self._config.notify_email)
        except Exception:
            logger.exception("Ошибка отправки email-уведомления о заявке")
