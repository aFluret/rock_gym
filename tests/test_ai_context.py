from pathlib import Path

from bot.ai.context_manager import get_optimized_context
from database.db import init_database
from database.queries import save_message


def test_context_deduplicates_messages(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    init_database(database_path)
    save_message(database_path, 1, "user", "Привет")
    save_message(database_path, 1, "user", "Привет")
    save_message(database_path, 1, "assistant", "Здравствуйте")

    context = get_optimized_context(database_path, 1)
    user_messages = [item for item in context if item["role"] == "user"]

    assert len(user_messages) == 1
