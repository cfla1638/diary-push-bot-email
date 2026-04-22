from datetime import date
from pathlib import Path

from diary_push_bot.diary_parser import DiaryParser


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_find_entries_for_month_day_matches_multiple_years(tmp_path: Path) -> None:
    _write(
        tmp_path / "2024" / "2024-4.md",
        "# 2024 - 4\n\n## 23 星期二\n\n2024 entry\n\n## 24 星期三\n\nother day\n",
    )
    _write(
        tmp_path / "2025" / "2025-04.md",
        "# 2025 - 4\n\n## 23 星期三\n\n2025 entry\n",
    )

    entries = DiaryParser(tmp_path).find_entries_for_month_day(date(2026, 4, 23))

    assert [entry.entry_date.year for entry in entries] == [2024, 2025]
    assert [entry.body for entry in entries] == ["2024 entry", "2025 entry"]


def test_find_entries_ignores_nonstandard_paths(tmp_path: Path) -> None:
    _write(tmp_path / "2010-" / "我的回忆.md", "## 23\n\nshould ignore\n")
    _write(tmp_path / "想法索引.md", "## 23\n\nshould ignore\n")
    _write(tmp_path / "2024" / "notes.md", "## 23\n\nshould ignore\n")
    _write(tmp_path / "2024" / "2025-04.md", "## 23\n\nwrong year\n")
    _write(tmp_path / "2024" / "2024-04.md", "# 2024-04\n\n## 23 星期二\n\nkeep me\n")

    entries = DiaryParser(tmp_path).find_entries_for_month_day(date(2026, 4, 23))

    assert len(entries) == 1
    assert entries[0].body == "keep me"


def test_find_entries_keeps_markdown_image_lines(tmp_path: Path) -> None:
    _write(
        tmp_path / "2024" / "2024-04.md",
        "# 2024 - 4\n\n## 23 星期二\n\nhello\n\n![img](https://example.com/a.png)\n\nworld\n",
    )

    entry = DiaryParser(tmp_path).find_entries_for_month_day(date(2026, 4, 23))[0]

    assert "![img](https://example.com/a.png)" in entry.body


def test_find_entries_returns_empty_when_day_missing(tmp_path: Path) -> None:
    _write(tmp_path / "2024" / "2024-04.md", "# 2024 - 4\n\n## 22 星期一\n\nnope\n")

    entries = DiaryParser(tmp_path).find_entries_for_month_day(date(2026, 4, 23))

    assert entries == []
