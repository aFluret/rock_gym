from pathlib import Path

from database.db import init_database
from database.queries import create_booking


def test_duplicate_booking_blocked(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    init_database(database_path)

    first_result, first_id = create_booking(database_path, None, "Иван", "+375291234567", "minsk")
    second_result, duplicate_id = create_booking(database_path, None, "Иван", "+375291234567", "minsk")

    assert first_result is True
    assert first_id is not None
    assert second_result is False
    assert duplicate_id == first_id
