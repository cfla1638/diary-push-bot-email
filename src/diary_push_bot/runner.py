from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage

from diary_push_bot.config import AppConfig
from diary_push_bot.diary_parser import DiaryEntry, DiaryParser
from diary_push_bot.mailer import build_message, send_message
from diary_push_bot.selector import DiarySelector
from diary_push_bot.state_store import StateStore


@dataclass(frozen=True)
class RunResult:
    sent: bool
    entry: DiaryEntry | None
    message_preview: str | None
    skipped_as_already_sent: bool = False


def render_message_preview(message: EmailMessage) -> str:
    body = message.get_body(preferencelist=("plain",))
    content = body.get_content() if body is not None else ""
    subject = str(message.get("Subject", ""))
    sender = str(message.get("From", ""))
    recipient = str(message.get("To", ""))
    return "\n".join(
        [
            f"From: {sender}",
            f"To: {recipient}",
            f"Subject: {subject}",
            "",
            content.rstrip(),
        ]
    )


class DiaryPushRunner:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.parser = DiaryParser(config.diary_root)
        self.selector = DiarySelector(self.parser)
        self.state_store = StateStore(config.state_file)

    def preview(self, target_date: date) -> RunResult:
        entry = self.selector.pick_entry(target_date)
        if entry is None:
            return RunResult(sent=False, entry=None, message_preview=None)
        message = build_message(self.config, entry)
        return RunResult(sent=False, entry=entry, message_preview=render_message_preview(message))

    def send_for_date(self, target_date: date) -> RunResult:
        entry = self.selector.pick_entry(target_date)
        if entry is None:
            return RunResult(sent=False, entry=None, message_preview=None)
        message = build_message(self.config, entry)
        send_message(self.config, message)
        return RunResult(sent=True, entry=entry, message_preview=render_message_preview(message))

    def send_for_date_once(self, target_date: date, sent_at: datetime) -> RunResult:
        if self.state_store.has_sent_for_date(target_date):
            return RunResult(sent=False, entry=None, message_preview=None, skipped_as_already_sent=True)

        result = self.send_for_date(target_date)
        if result.sent and result.entry is not None:
            self.state_store.mark_sent(target_date, result.entry, sent_at)
        return result
