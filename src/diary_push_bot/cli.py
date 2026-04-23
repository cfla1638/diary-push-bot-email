from __future__ import annotations

import argparse
from datetime import date, datetime, time as dt_time, timedelta
import hashlib
import sys
import time
from zoneinfo import ZoneInfo

from diary_push_bot.config import AppConfig, load_config
from diary_push_bot.runner import DiaryPushRunner, RunResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="diary-push-bot")
    parser.add_argument("command", choices=["preview", "send-once", "serve"])
    parser.add_argument("--env-file", default=None)
    return parser


def _parse_clock_time(value: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = value.split(":", maxsplit=1)
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError as exc:
        raise ValueError(f"Invalid time value: {value}") from exc

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time value: {value}")
    return hour, minute


def _parse_push_time_range(config: AppConfig) -> tuple[tuple[int, int], tuple[int, int]]:
    try:
        start_text, end_text = config.push_time_range.split("-", maxsplit=1)
    except ValueError as exc:
        raise ValueError(f"Invalid PUSH_TIME_RANGE format: {config.push_time_range}") from exc

    start = _parse_clock_time(start_text)
    end = _parse_clock_time(end_text)
    start_minutes = start[0] * 60 + start[1]
    end_minutes = end[0] * 60 + end[1]
    if end_minutes < start_minutes:
        raise ValueError("PUSH_TIME_RANGE cannot cross midnight")
    return start, end


def _now(config: AppConfig) -> datetime:
    return datetime.now(ZoneInfo(config.timezone_name))


def _daily_run_at(config: AppConfig, target_date: date) -> datetime:
    start, end = _parse_push_time_range(config)
    start_minutes = start[0] * 60 + start[1]
    end_minutes = end[0] * 60 + end[1]
    span = end_minutes - start_minutes

    if span == 0:
        chosen_minutes = start_minutes
    else:
        seed_input = f"{target_date.isoformat()}|{config.push_time_range}|{config.timezone_name}"
        seed = int(hashlib.sha256(seed_input.encode("utf-8")).hexdigest(), 16)
        chosen_minutes = start_minutes + (seed % (span + 1))

    hour, minute = divmod(chosen_minutes, 60)
    timezone = ZoneInfo(config.timezone_name)
    return datetime.combine(target_date, dt_time(hour=hour, minute=minute), tzinfo=timezone)


def _is_within_push_window(config: AppConfig, current: datetime) -> bool:
    start, end = _parse_push_time_range(config)
    start_minutes = start[0] * 60 + start[1]
    end_minutes = end[0] * 60 + end[1]
    current_minutes = current.hour * 60 + current.minute
    return start_minutes <= current_minutes <= end_minutes


def _next_run_at(config: AppConfig, current: datetime) -> datetime:
    today_target = _daily_run_at(config, current.date())
    if today_target > current:
        return today_target
    return _daily_run_at(config, current.date() + timedelta(days=1))


def _print_result(result: RunResult, command: str) -> int:
    if result.entry is None:
        print("今天没有可发送的历史日记。")
        return 0

    print(f"已选中：{result.entry.entry_date:%Y-%m-%d} {result.entry.source_path}")
    if command == "preview":
        print(result.message_preview or "")
    elif command == "send-once":
        print("邮件发送成功。")
    return 0


def _serve_once(config: AppConfig, runner: DiaryPushRunner, target_datetime: datetime) -> None:
    result = runner.send_for_date_once(target_datetime.date(), target_datetime)
    if result.skipped_as_already_sent:
        print(f"{target_datetime.date()} 今天已经推送过，跳过。")
    elif result.entry is None:
        print(f"{target_datetime.date()} 没有可发送的历史日记。")
    else:
        print(f"{target_datetime.date()} 邮件发送成功：{result.entry.source_path}")


def _run_startup_catchup(config: AppConfig, runner: DiaryPushRunner, current: datetime) -> None:
    if not _is_within_push_window(config, current):
        return
    _serve_once(config, runner, current)


def run_preview_or_send(command: str, env_file: str | None) -> int:
    config = load_config(env_file)
    runner = DiaryPushRunner(config)
    today = _now(config).date()
    result = runner.preview(today) if command == "preview" else runner.send_for_date(today)
    return _print_result(result, command)


def run_serve(env_file: str | None) -> int:
    config = load_config(env_file)
    runner = DiaryPushRunner(config)

    print(f"调度器已启动，时区：{config.timezone_name}，推送时间范围：{config.push_time_range}")
    _run_startup_catchup(config, runner, _now(config))

    while True:
        current = _now(config)
        next_run = _next_run_at(config, current)
        sleep_seconds = max((next_run - current).total_seconds(), 0)
        print(f"下一次执行时间：{next_run.isoformat()}")
        time.sleep(sleep_seconds)
        _serve_once(config, runner, next_run)


def serve_once_for_datetime(config: AppConfig, runner: DiaryPushRunner, target_datetime: datetime) -> None:
    _serve_once(config, runner, target_datetime)


def run_startup_catchup(config: AppConfig, runner: DiaryPushRunner, current: datetime) -> None:
    _run_startup_catchup(config, runner, current)


def get_next_run_at(config: AppConfig, current: datetime) -> datetime:
    return _next_run_at(config, current)


def parse_push_time_range(config: AppConfig) -> tuple[tuple[int, int], tuple[int, int]]:
    return _parse_push_time_range(config)


def get_daily_run_at(config: AppConfig, target_date: date) -> datetime:
    return _daily_run_at(config, target_date)


def is_within_push_window(config: AppConfig, current: datetime) -> bool:
    return _is_within_push_window(config, current)


def get_now(config: AppConfig) -> datetime:
    return _now(config)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "serve":
            return run_serve(args.env_file)
        return run_preview_or_send(args.command, args.env_file)
    except KeyboardInterrupt:
        print("已停止。")
        return 0
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
