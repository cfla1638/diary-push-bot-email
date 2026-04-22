from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    diary_root: Path
    recipient_email: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_sender: str
    smtp_starttls: bool
    smtp_ssl: bool
    send_time: str
    timezone_name: str


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _parse_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean environment variable {name}: {value}")


def load_config(env_file: str | None = None) -> AppConfig:
    load_dotenv(env_file)

    diary_root = Path(_require_env("DIARY_ROOT")).expanduser().resolve()
    if not diary_root.exists() or not diary_root.is_dir():
        raise ValueError(f"DIARY_ROOT does not exist or is not a directory: {diary_root}")

    smtp_ssl = _parse_bool("SMTP_SSL", default=False)
    smtp_starttls = _parse_bool("SMTP_STARTTLS", default=not smtp_ssl)

    if smtp_ssl and smtp_starttls:
        raise ValueError("SMTP_SSL and SMTP_STARTTLS cannot both be enabled")

    return AppConfig(
        diary_root=diary_root,
        recipient_email=_require_env("RECIPIENT_EMAIL"),
        smtp_host=_require_env("SMTP_HOST"),
        smtp_port=int(_require_env("SMTP_PORT")),
        smtp_username=_require_env("SMTP_USERNAME"),
        smtp_password=_require_env("SMTP_PASSWORD"),
        smtp_sender=os.getenv("SMTP_SENDER", "").strip() or _require_env("SMTP_USERNAME"),
        smtp_starttls=smtp_starttls,
        smtp_ssl=smtp_ssl,
        send_time=_require_env("SEND_TIME"),
        timezone_name=os.getenv("TIMEZONE", "Asia/Shanghai").strip() or "Asia/Shanghai",
    )
