from __future__ import annotations

import argparse
from datetime import datetime, timedelta
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


def _parse_send_time(config: AppConfig) -> tuple[int, int]:
    try:
        hour_text, minute_text = config.send_time.split(":", maxsplit=1)
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError as exc:
        raise ValueError(f"Invalid SEND_TIME format: {config.send_time}") from exc

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid SEND_TIME value: {config.send_time}")
    return hour, minute


def _now(config: AppConfig) -> datetime:
    return datetime.now(ZoneInfo(config.timezone_name))


def _next_run_at(config: AppConfig, current: datetime) -> datetime:
    hour, minute = _parse_send_time(config)
    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= current:
        target += timedelta(days=1)
    return target


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
    result = runner.send_for_date(target_datetime.date())
    if result.entry is None:
        print(f"{target_datetime.date()} 没有可发送的历史日记。")
    else:
        print(f"{target_datetime.date()} 邮件发送成功：{result.entry.source_path}")


def run_preview_or_send(command: str, env_file: str | None) -> int:
    config = load_config(env_file)
    runner = DiaryPushRunner(config)
    today = _now(config).date()
    result = runner.preview(today) if command == "preview" else runner.send_for_date(today)
    return _print_result(result, command)


def run_serve(env_file: str | None) -> int:
    config = load_config(env_file)
    runner = DiaryPushRunner(config)

    print(f"调度器已启动，时区：{config.timezone_name}，发送时间：{config.send_time}")
    while True:
        current = _now(config)
        next_run = _next_run_at(config, current)
        sleep_seconds = max((next_run - current).total_seconds(), 0)
        print(f"下一次执行时间：{next_run.isoformat()}")
        time.sleep(sleep_seconds)
        _serve_once(config, runner, next_run)


def serve_once_for_datetime(config: AppConfig, runner: DiaryPushRunner, target_datetime: datetime) -> None:
    _serve_once(config, runner, target_datetime)


def get_next_run_at(config: AppConfig, current: datetime) -> datetime:
    return _next_run_at(config, current)


def parse_send_time(config: AppConfig) -> tuple[int, int]:
    return _parse_send_time(config)


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
