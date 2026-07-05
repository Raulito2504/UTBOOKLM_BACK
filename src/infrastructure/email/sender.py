from dataclasses import dataclass

from src.core.config import get_settings


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailSender:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def send(self, message: EmailMessage) -> bool:
        return bool(message.to and message.subject and self.settings.email_from)


def get_email_sender() -> EmailSender:
    return EmailSender()
