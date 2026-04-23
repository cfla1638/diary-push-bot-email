from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path

from diary_push_bot.diary_parser import DiaryEntry


@dataclass(frozen=True)
class SentRecord:
    target_date: date
    sent_at: str
    source_path: str


class StateStore:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file

    def has_sent_for_date(self, target_date: date) -> bool:
        state = self._load_state()
        return target_date.isoformat() in state.get("sent_dates", {})

    def mark_sent(self, target_date: date, entry: DiaryEntry, sent_at: datetime) -> None:
        state = self._load_state()
        sent_dates = state.setdefault("sent_dates", {})
        sent_dates[target_date.isoformat()] = {
            "sent_at": sent_at.isoformat(),
            "source_path": str(entry.source_path),
        }
        self._write_state(state)

    def _load_state(self) -> dict:
        if not self.state_file.exists():
            return {"sent_dates": {}}
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def _write_state(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
