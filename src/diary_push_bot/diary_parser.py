from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re

MONTH_FILE_PATTERN = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{1,2})\.md$")
DAY_HEADING_PATTERN = re.compile(r"^##\s+(?P<day>\d+)\b.*$", re.MULTILINE)
YEAR_DIR_PATTERN = re.compile(r"^\d{4}$")


@dataclass(frozen=True)
class DiaryEntry:
    entry_date: date
    title_line: str
    body: str
    source_path: Path


class DiaryParser:
    def __init__(self, diary_root: Path) -> None:
        self.diary_root = diary_root

    def find_entries_for_month_day(self, target_date: date) -> list[DiaryEntry]:
        entries: list[DiaryEntry] = []
        month = target_date.month
        day = target_date.day

        for year_dir in sorted(self.diary_root.iterdir()):
            if not year_dir.is_dir() or not YEAR_DIR_PATTERN.fullmatch(year_dir.name):
                continue

            month_files = self._find_month_files(year_dir, month)
            for month_file in month_files:
                entry = self._extract_entry(month_file, int(year_dir.name), month, day)
                if entry is not None:
                    entries.append(entry)

        return entries

    def _find_month_files(self, year_dir: Path, month: int) -> list[Path]:
        matches: list[Path] = []
        for candidate in year_dir.iterdir():
            if not candidate.is_file() or candidate.suffix.lower() != ".md":
                continue
            match = MONTH_FILE_PATTERN.fullmatch(candidate.name)
            if match is None:
                continue
            if int(match.group("year")) != int(year_dir.name):
                continue
            if int(match.group("month")) != month:
                continue
            matches.append(candidate)
        return sorted(matches)

    def _extract_entry(self, file_path: Path, year: int, month: int, day: int) -> DiaryEntry | None:
        content = file_path.read_text(encoding="utf-8")
        matches = list(DAY_HEADING_PATTERN.finditer(content))
        for index, match in enumerate(matches):
            if int(match.group("day")) != day:
                continue
            body_start = match.end()
            body_end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            body = content[body_start:body_end].strip()
            return DiaryEntry(
                entry_date=date(year, month, day),
                title_line=match.group(0).strip(),
                body=body,
                source_path=file_path,
            )
        return None
