from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Booking:
    id: int
    user_id: int | None
    name: str
    phone: str
    gym_location: str
    status: str
    created_at: datetime
    contacted_at: datetime | None
