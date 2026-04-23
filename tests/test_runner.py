from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import random

import pytest

from diary_push_bot.cli import get_daily_run_at, get_next_run_at, is_within_push_window, parse_push_time_range, run_startup_catchup
from diary_push_bot.config import AppConfig
from diary_push_bot.diary_parser import DiaryParser
from diary_push_bot.runner import DiaryPushRunner
from diary_push_bot.selector import DiarySelector
from diary_push_bot.state_store import StateStore


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
        state_file=tmp_path / ".diary_push_state.json",
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


def test_is_within_push_window_returns_true_inside_range(tmp_path: Path) -> None:
    config = _config(tmp_path, "09:00-11:00")
    current = datetime(2026, 4, 23, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    assert is_within_push_window(config, current) is True


def test_is_within_push_window_returns_false_outside_range(tmp_path: Path) -> None:
    config = _config(tmp_path, "09:00-11:00")
    current = datetime(2026, 4, 23, 8, 59, tzinfo=ZoneInfo("Asia/Shanghai"))

    assert is_within_push_window(config, current) is False


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


def test_state_store_marks_sent_date(tmp_path: Path) -> None:
    _write(tmp_path / "2024" / "2024-04.md", "# 2024 - 4\n\n## 23 星期二\n\nbody\n")
    entry = DiaryParser(tmp_path).find_entries_for_month_day(date(2026, 4, 23))[0]
    store = StateStore(tmp_path / ".diary_push_state.json")

    store.mark_sent(date(2026, 4, 23), entry, datetime(2026, 4, 23, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")))

    assert store.has_sent_for_date(date(2026, 4, 23)) is True
    state = json.loads((tmp_path / ".diary_push_state.json").read_text(encoding="utf-8"))
    assert "2026-04-23" in state["sent_dates"]


def test_send_for_date_once_skips_when_already_sent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path / "2024" / "2024-04.md", "# 2024 - 4\n\n## 23 星期二\n\nbody\n")
    config = _config(tmp_path)
    runner = DiaryPushRunner(config)
    runner.state_store.mark_sent(
        date(2026, 4, 23),
        runner.parser.find_entries_for_month_day(date(2026, 4, 23))[0],
        datetime(2026, 4, 23, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    called = False

    def fake_send(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("diary_push_bot.runner.send_message", fake_send)

    result = runner.send_for_date_once(date(2026, 4, 23), datetime(2026, 4, 23, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")))

    assert result.sent is False
    assert result.skipped_as_already_sent is True
    assert called is False


def test_send_for_date_once_marks_state_only_after_send(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path / "2024" / "2024-04.md", "# 2024 - 4\n\n## 23 星期二\n\nbody\n")
    config = _config(tmp_path)
    runner = DiaryPushRunner(config)

    monkeypatch.setattr("diary_push_bot.runner.send_message", lambda *args, **kwargs: None)

    result = runner.send_for_date_once(date(2026, 4, 23), datetime(2026, 4, 23, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")))

    assert result.sent is True
    assert runner.state_store.has_sent_for_date(date(2026, 4, 23)) is True


def test_send_for_date_once_without_candidate_does_not_mark_sent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path / "2024" / "2024-04.md", "# 2024 - 4\n\n## 24 星期三\n\nbody\n")
    config = _config(tmp_path)
    runner = DiaryPushRunner(config)

    monkeypatch.setattr("diary_push_bot.runner.send_message", lambda *args, **kwargs: None)

    result = runner.send_for_date_once(date(2026, 4, 23), datetime(2026, 4, 23, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")))

    assert result.sent is False
    assert runner.state_store.has_sent_for_date(date(2026, 4, 23)) is False


def test_run_startup_catchup_sends_immediately_inside_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path / "2024" / "2024-04.md", "# 2024 - 4\n\n## 23 星期二\n\nbody\n")
    config = _config(tmp_path, "09:00-11:00")
    runner = DiaryPushRunner(config)

    monkeypatch.setattr("diary_push_bot.runner.send_message", lambda *args, **kwargs: None)

    run_startup_catchup(config, runner, datetime(2026, 4, 23, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")))

    assert runner.state_store.has_sent_for_date(date(2026, 4, 23)) is True


def test_run_startup_catchup_skips_outside_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path / "2024" / "2024-04.md", "# 2024 - 4\n\n## 23 星期二\n\nbody\n")
    config = _config(tmp_path, "09:00-11:00")
    runner = DiaryPushRunner(config)

    monkeypatch.setattr("diary_push_bot.runner.send_message", lambda *args, **kwargs: None)

    run_startup_catchup(config, runner, datetime(2026, 4, 23, 8, 0, tzinfo=ZoneInfo("Asia/Shanghai")))

    assert runner.state_store.has_sent_for_date(date(2026, 4, 23)) is False


def test_run_startup_catchup_skips_if_already_sent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path / "2024" / "2024-04.md", "# 2024 - 4\n\n## 23 星期二\n\nbody\n")
    config = _config(tmp_path, "09:00-11:00")
    runner = DiaryPushRunner(config)

    monkeypatch.setattr("diary_push_bot.runner.send_message", lambda *args, **kwargs: None)

    run_startup_catchup(config, runner, datetime(2026, 4, 23, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")))
    state_before = (tmp_path / ".diary_push_state.json").read_text(encoding="utf-8")
    run_startup_catchup(config, runner, datetime(2026, 4, 23, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")))
    state_after = (tmp_path / ".diary_push_state.json").read_text(encoding="utf-8")

    assert state_before == state_after
