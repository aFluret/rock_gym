from __future__ import annotations

from datetime import datetime


def human_time_diff(from_dt: datetime, to_dt: datetime | None = None) -> str:
    reference = to_dt or datetime.utcnow()
    seconds = max(int((reference - from_dt).total_seconds()), 0)
    if seconds < 60:
        return "только что"
    if seconds < 3600:
        return f"{seconds // 60} мин назад"
    if seconds < 86400:
        return f"{seconds // 3600} ч назад"
    return f"{seconds // 86400} дн назад"
