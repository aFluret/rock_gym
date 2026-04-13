from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import re


_TEXT_TIMELINE: dict[int, deque[tuple[datetime, str]]] = defaultdict(deque)


def _normalize_text(text: str) -> str:
    lowered = text.lower().strip()
    compacted = re.sub(r"\s+", " ", lowered)
    letters_only = re.sub(r"[^\w\s]", "", compacted)
    return letters_only


def check_text_spam(user_id: int, text: str) -> tuple[bool, str | None]:
    normalized = _normalize_text(text)
    if len(normalized) < 2:
        return False, None

    now = datetime.now(timezone.utc)
    queue = _TEXT_TIMELINE[user_id]
    lower_bound = now - timedelta(seconds=45)
    while queue and queue[0][0] < lower_bound:
        queue.popleft()

    recent_duplicates = sum(1 for _, value in queue if value == normalized)
    queue.append((now, normalized))

    if recent_duplicates >= 2:
        return True, "Похоже, это повтор сообщения. Напишите чуть подробнее, чтобы я точнее помог."

    if len(queue) >= 8:
        unique_messages = {value for _, value in queue}
        if len(unique_messages) <= 2:
            return True, "Вижу частые однотипные сообщения. Давайте продолжим спокойно, по одному вопросу."
    return False, None
