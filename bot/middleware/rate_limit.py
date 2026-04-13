from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta


_USER_WINDOWS: dict[int, deque[datetime]] = defaultdict(deque)


def is_rate_limited(user_id: int, limit_per_minute: int) -> bool:
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=1)
    queue = _USER_WINDOWS[user_id]
    while queue and queue[0] < window_start:
        queue.popleft()
    if len(queue) >= limit_per_minute:
        return True
    queue.append(now)
    return False
