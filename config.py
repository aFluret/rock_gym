from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    groq_api_key: str
    groq_model: str
    database_path: Path
    admin_ids: tuple[int, ...]
    log_level: str
    crm_webhook_url: str
    groq_max_retries: int
    groq_retry_backoff_seconds: float
    rate_limit_per_minute: int = 15


def _parse_database_path(database_url: str) -> Path:
    if not database_url.startswith("sqlite:///"):
        return Path("rock_gym.db")
    return Path(database_url.replace("sqlite:///", "", 1))


def _parse_admin_ids(raw_admin_ids: str) -> tuple[int, ...]:
    if not raw_admin_ids.strip():
        return tuple()
    admin_ids = []
    for chunk in raw_admin_ids.split(","):
        value = chunk.strip()
        if not value:
            continue
        if value.isdigit():
            admin_ids.append(int(value))
    return tuple(admin_ids)


def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "sqlite:///rock_gym.db")
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        database_path=_parse_database_path(database_url),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        crm_webhook_url=os.getenv("CRM_WEBHOOK_URL", ""),
        groq_max_retries=int(os.getenv("GROQ_MAX_RETRIES", "3")),
        groq_retry_backoff_seconds=float(os.getenv("GROQ_RETRY_BACKOFF_SECONDS", "0.8")),
    )
