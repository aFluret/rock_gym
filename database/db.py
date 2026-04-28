from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator


def _schema() -> tuple[str, ...]:
    return (
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            phone TEXT,
            category TEXT CHECK(category IN ('student','schoolkid','adult','maternity')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            gym_location TEXT CHECK(gym_location IN ('minsk','lesnoy')),
            source TEXT DEFAULT 'telegram',
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','contacted','cancelled')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            contacted_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS admin_reminders (
            id INTEGER PRIMARY KEY,
            booking_id INTEGER NOT NULL UNIQUE,
            next_reminder_at DATETIME NOT NULL,
            reminder_count INTEGER DEFAULT 0,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INTEGER PRIMARY KEY,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('system', 'assistant', 'user')),
            content TEXT NOT NULL,
            is_important INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY,
            event_name TEXT NOT NULL,
            telegram_id INTEGER,
            booking_id INTEGER,
            payload TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS booking_sessions (
            telegram_id INTEGER PRIMARY KEY,
            state TEXT NOT NULL,
            payload TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS bot_admins (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            added_by INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'removed')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS admin_invites (
            id INTEGER PRIMARY KEY,
            token TEXT UNIQUE NOT NULL,
            created_by INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'used', 'expired')),
            used_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL,
            used_at DATETIME
        );
        """,
    )


def init_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        for query in _schema():
            conn.execute(query)
        conn.commit()


@contextmanager
def with_connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
