from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import random

import pytest

from diary_push_bot.cli import get_daily_run_at, get_next_run_at, parse_push_time_range
from diary_push_bot.config import AppConfig
from diary_push_bot.diary_parser import DiaryParser
from diary_push_bot.runner import DiaryPushRunner
from diary_push_bot.selector import DiarySelector


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _config(tmp_path: Path, push_time_range: str = "09:00-09:00") -> AppConfig:
    return AppConfig(
        diary_root=tmp_path,
        recipient_email="to@example.com",
        smtp_host="smtp.office365.com",
        smtp_port=587,
        smtp_username="sender@example.com",
        smtp_password="secret",
        smtp_sender="sender@example.com",
        smtp_starttls=True,
        smtp_ssl=False,
        push_time_range=push_time_range,
        timezone_name="Asia/Shanghai",
    )


def test_preview_returns_message_for_candidate(tmp_path: Path) -> None:
    _write(tmp_path / "2024" / "2024-04.md", "# 2024 - 4\n\n## 23 星期二\n\npreview body\n")
    config = _config(tmp_path)
    runner = DiaryPushRunner(config)

    result = runner.preview(date(2026, 4, 23))

    assert result.sent is False
    assert result.entry is not None
    assert "preview body" in (result.message_preview or "")
    assert "历史上的今天" in (result.message_preview or "")


def test_preview_returns_no_message_when_no_candidate(tmp_path: Path) -> None:
    _write(tmp_path / "2024" / "2024-04.md", "# 2024 - 4\n\n## 24 星期三\n\npreview body\n")
    config = _config(tmp_path)
    runner = DiaryPushRunner(config)

    result = runner.preview(date(2026, 4, 23))

    assert result.entry is None
    assert result.message_preview is None


def test_selector_chooses_from_candidates_with_seed(tmp_path: Path) -> None:
    _write(tmp_path / "2024" / "2024-04.md", "# 2024 - 4\n\n## 23 星期二\n\nfrom 2024\n")
    _write(tmp_path / "2025" / "2025-04.md", "# 2025 - 4\n\n## 23 星期三\n\nfrom 2025\n")

    selector = DiarySelector(DiaryParser(tmp_path), random.Random(1))
    entry = selector.pick_entry(date(2026, 4, 23))

    assert entry is not None
    assert entry.body in {"from 2024", "from 2025"}


def test_parse_push_time_range_parses_start_and_end(tmp_path: Path) -> None:
    start, end = parse_push_time_range(_config(tmp_path, "09:00-11:30"))

    assert start == (9, 0)
    assert end == (11, 30)


def test_parse_push_time_range_rejects_cross_midnight(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cross midnight"):
        parse_push_time_range(_config(tmp_path, "23:00-01:00"))


def test_daily_run_at_is_fixed_when_range_start_equals_end(tmp_path: Path) -> None:
    config = _config(tmp_path, "09:00-09:00")

    run_at = get_daily_run_at(config, date(2026, 4, 23))

    assert run_at == datetime(2026, 4, 23, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def test_daily_run_at_is_stable_for_same_day(tmp_path: Path) -> None:
    config = _config(tmp_path, "09:00-11:00")

    first = get_daily_run_at(config, date(2026, 4, 23))
    second = get_daily_run_at(config, date(2026, 4, 23))

    assert first == second
    assert first.date() == date(2026, 4, 23)
    assert datetime(2026, 4, 23, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai")) <= first <= datetime(2026, 4, 23, 11, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def test_get_next_run_at_returns_today_if_future(tmp_path: Path) -> None:
    config = _config(tmp_path, "09:00-09:00")
    current = datetime(2026, 4, 23, 8, 30, tzinfo=ZoneInfo("Asia/Shanghai"))

    next_run = get_next_run_at(config, current)

    assert next_run == datetime(2026, 4, 23, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def test_get_next_run_at_rolls_to_next_day_if_passed(tmp_path: Path) -> None:
    config = _config(tmp_path, "09:00-09:00")
    current = datetime(2026, 4, 23, 9, 0, 1, tzinfo=ZoneInfo("Asia/Shanghai"))

    next_run = get_next_run_at(config, current)

    assert next_run == datetime(2026, 4, 24, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
