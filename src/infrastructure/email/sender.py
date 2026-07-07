from dataclasses import dataclass
from html import escape
import logging

from src.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str
    to_name: str | None = None
    html_body: str | None = None


class EmailSender:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def send(self, message: EmailMessage) -> bool:
        if not message.to or not message.subject or not self.settings.email_from:
            logger.warning("Email message skipped because required fields are missing")
            return False

        if not self.settings.email_enabled:
            return True

        provider = self.settings.email_provider.lower()
        if provider == "brevo":
            return await self._send_with_brevo(message)

        logger.warning("Email provider is not supported", extra={"provider": provider})
        return False

    async def _send_with_brevo(self, message: EmailMessage) -> bool:
        if not self.settings.brevo_api_key:
            logger.error("Brevo email delivery is enabled but BREVO_API_KEY is missing")
            return False

        try:
            from brevo import AsyncBrevo
            from brevo.transactional_emails import (
                SendTransacEmailRequestSender,
                SendTransacEmailRequestToItem,
            )
        except ImportError:
            logger.exception("Brevo SDK is not installed")
            return False

        client = AsyncBrevo(api_key=self.settings.brevo_api_key)
        html_content = message.html_body or self._text_to_html(message.body)
        recipient = {"email": message.to}
        if message.to_name:
            recipient["name"] = message.to_name

        try:
            await client.transactional_emails.send_transac_email(
                subject=message.subject,
                html_content=html_content,
                sender=SendTransacEmailRequestSender(
                    name=self.settings.email_from_name,
                    email=self.settings.email_from,
                ),
                to=[
                    SendTransacEmailRequestToItem(
                        **recipient,
                    )
                ],
                request_options={"timeout_in_seconds": 10, "max_retries": 1},
            )
        except Exception:
            logger.exception("Brevo email delivery failed")
            return False

        return True

    @staticmethod
    def _text_to_html(body: str) -> str:
        escaped_lines = (escape(line) for line in body.splitlines())
        return "<html><body><p>" + "<br>".join(escaped_lines) + "</p></body></html>"


def get_email_sender() -> EmailSender:
    return EmailSender()
