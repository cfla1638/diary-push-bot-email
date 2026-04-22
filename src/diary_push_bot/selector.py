from __future__ import annotations

from datetime import date
import random

from diary_push_bot.diary_parser import DiaryEntry, DiaryParser


class DiarySelector:
    def __init__(self, parser: DiaryParser, randomizer: random.Random | None = None) -> None:
        self.parser = parser
        self.randomizer = randomizer or random.Random()

    def list_candidates(self, target_date: date) -> list[DiaryEntry]:
        return self.parser.find_entries_for_month_day(target_date)

    def pick_entry(self, target_date: date) -> DiaryEntry | None:
        entries = self.list_candidates(target_date)
        if not entries:
            return None
        return self.randomizer.choice(entries)
