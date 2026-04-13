from pathlib import Path

from database.db import init_database
from database.queries import (
    clear_booking_session,
    get_booking_session,
    get_funnel_stats,
    track_event,
    upsert_booking_session,
)


def test_funnel_stats_counts_and_conversion(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    init_database(database_path)

    for _ in range(4):
        track_event(database_path, "start", telegram_id=1)
    for _ in range(2):
        track_event(database_path, "booking_started", telegram_id=1)
    track_event(database_path, "booking_confirmed", telegram_id=1, booking_id=42)

    stats = get_funnel_stats(database_path, days=30)
    assert stats["start"] == 4
    assert stats["booking_started"] == 2
    assert stats["booking_confirmed"] == 1
    assert stats["start_to_booking_started"] == 50.0


def test_booking_session_persisted_and_cleared(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    init_database(database_path)

    upsert_booking_session(database_path, 100, "book_phone", {"booking_name": "Анна"})
    session = get_booking_session(database_path, 100)
    assert session is not None
    assert session["state"] == "book_phone"
    assert session["payload"]["booking_name"] == "Анна"

    clear_booking_session(database_path, 100)
    assert get_booking_session(database_path, 100) is None
