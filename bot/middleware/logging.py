from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_level: str = "INFO") -> None:
    logs_path = Path("logs")
    logs_path.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        logs_path / "bot.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logging.basicConfig(level=log_level.upper(), handlers=[handler, logging.StreamHandler()])
