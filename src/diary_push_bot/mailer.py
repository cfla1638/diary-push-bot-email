from __future__ import annotations

from email.message import EmailMessage
import smtplib

from diary_push_bot.config import AppConfig
from diary_push_bot.diary_parser import DiaryEntry


def build_message(config: AppConfig, entry: DiaryEntry) -> EmailMessage:
    message = EmailMessage()
    message["From"] = config.smtp_sender
    message["To"] = config.recipient_email
    message["Subject"] = f"历史上的今天 | {entry.entry_date:%m-%d} | {entry.entry_date:%Y}"
    message.set_content(
        "\n".join(
            [
                f"日期：{entry.entry_date:%Y-%m-%d}",
                f"标题：{entry.title_line}",
                f"来源：{entry.source_path}",
                "",
                entry.body,
            ]
        )
    )
    return message


def send_message(config: AppConfig, message: EmailMessage) -> None:
    if config.smtp_ssl:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as client:
            client.login(config.smtp_username, config.smtp_password)
            client.send_message(message)
        return

    with smtplib.SMTP(config.smtp_host, config.smtp_port) as client:
        if config.smtp_starttls:
            client.starttls()
        client.login(config.smtp_username, config.smtp_password)
        client.send_message(message)
