from __future__ import annotations

import json
import secrets
from pathlib import Path
from sqlite3 import Row
from typing import Any

from database.db import with_connection


def upsert_user(
    database_path: Path,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    phone: str | None = None,
    category: str | None = None,
) -> int:
    with with_connection(database_path) as conn:
        conn.execute(
            """
            INSERT INTO users(telegram_id, username, first_name, phone, category)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                phone=COALESCE(excluded.phone, users.phone),
                category=COALESCE(excluded.category, users.category)
            """,
            (telegram_id, username, first_name, phone, category),
        )
        row = conn.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
        return int(row["id"])


def save_message(
    database_path: Path,
    conversation_id: int,
    role: str,
    content: str,
    is_important: bool = False,
) -> None:
    with with_connection(database_path) as conn:
        conn.execute(
            """
            INSERT INTO conversation_messages(conversation_id, role, content, is_important)
            VALUES(?, ?, ?, ?)
            """,
            (conversation_id, role, content, int(is_important)),
        )


def fetch_conversation_messages(database_path: Path, conversation_id: int) -> list[Row]:
    with with_connection(database_path) as conn:
        rows = conn.execute(
            """
            SELECT role, content, is_important, created_at
            FROM conversation_messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()
    return rows


def create_booking(
    database_path: Path,
    user_id: int | None,
    name: str,
    phone: str,
    gym_location: str,
) -> tuple[bool, int | None]:
    with with_connection(database_path) as conn:
        duplicate = conn.execute(
            """
            SELECT id
            FROM bookings
            WHERE phone = ? AND gym_location = ? AND status IN ('pending', 'contacted')
            ORDER BY id DESC
            LIMIT 1
            """,
            (phone, gym_location),
        ).fetchone()
        if duplicate:
            return False, int(duplicate["id"])
        cursor = conn.execute(
            """
            INSERT INTO bookings(user_id, name, phone, gym_location)
            VALUES(?, ?, ?, ?)
            """,
            (user_id, name, phone, gym_location),
        )
        return True, int(cursor.lastrowid)


def get_booking_by_id(database_path: Path, booking_id: int) -> Row | None:
    with with_connection(database_path) as conn:
        row = conn.execute(
            """
            SELECT b.*, u.telegram_id
            FROM bookings b
            LEFT JOIN users u ON u.id = b.user_id
            WHERE b.id = ?
            """,
            (booking_id,),
        ).fetchone()
    return row


def get_pending_bookings(database_path: Path) -> list[Row]:
    with with_connection(database_path) as conn:
        rows = conn.execute(
            """
            SELECT id, name, phone, gym_location, status, created_at
            FROM bookings
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 20
            """
        ).fetchall()
    return rows


def mark_booking_contacted(database_path: Path, booking_id: int) -> bool:
    with with_connection(database_path) as conn:
        cursor = conn.execute(
            """
            UPDATE bookings
            SET status = 'contacted', contacted_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'pending'
            """,
            (booking_id,),
        )
        conn.execute(
            "DELETE FROM admin_reminders WHERE booking_id = ?",
            (booking_id,),
        )
    return cursor.rowcount > 0


def save_reminder(database_path: Path, booking_id: int, minutes: int) -> None:
    with with_connection(database_path) as conn:
        conn.execute(
            """
            INSERT INTO admin_reminders(booking_id, next_reminder_at, reminder_count)
            VALUES (?, DATETIME(CURRENT_TIMESTAMP, ?), 0)
            ON CONFLICT(booking_id) DO UPDATE SET
                next_reminder_at=excluded.next_reminder_at
            """,
            (booking_id, f"+{minutes} minutes"),
        )


def get_due_reminders(database_path: Path) -> list[Row]:
    with with_connection(database_path) as conn:
        rows = conn.execute(
            """
            SELECT ar.id, ar.booking_id, ar.reminder_count, b.name, b.phone, b.gym_location
            FROM admin_reminders ar
            JOIN bookings b ON b.id = ar.booking_id
            WHERE ar.next_reminder_at <= CURRENT_TIMESTAMP AND b.status = 'pending'
            ORDER BY ar.next_reminder_at ASC
            """
        ).fetchall()
    return rows


def ensure_pending_reminders(database_path: Path, minutes: int = 10) -> int:
    with with_connection(database_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO admin_reminders(booking_id, next_reminder_at, reminder_count)
            SELECT b.id, DATETIME(b.created_at, ?), 0
            FROM bookings b
            LEFT JOIN admin_reminders ar ON ar.booking_id = b.id
            WHERE b.status = 'pending' AND ar.id IS NULL
            """,
            (f"+{minutes} minutes",),
        )
    return cursor.rowcount


def bump_reminder(database_path: Path, reminder_id: int, next_minutes: int = 10) -> None:
    with with_connection(database_path) as conn:
        conn.execute(
            """
            UPDATE admin_reminders
            SET reminder_count = reminder_count + 1,
                next_reminder_at = DATETIME(CURRENT_TIMESTAMP, ?)
            WHERE id = ?
            """,
            (f"+{next_minutes} minutes", reminder_id),
        )


def get_stats_snapshot(database_path: Path) -> dict[str, Any]:
    with with_connection(database_path) as conn:
        totals = conn.execute(
            """
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
              SUM(CASE WHEN status = 'contacted' THEN 1 ELSE 0 END) AS contacted
            FROM bookings
            """
        ).fetchone()
    total = int(totals["total"] or 0)
    pending = int(totals["pending"] or 0)
    contacted = int(totals["contacted"] or 0)
    conversion = round((contacted / total) * 100, 1) if total else 0.0
    return {
        "total": total,
        "pending": pending,
        "contacted": contacted,
        "conversion": conversion,
    }


def get_all_user_telegram_ids(database_path: Path) -> list[int]:
    with with_connection(database_path) as conn:
        rows = conn.execute(
            """
            SELECT telegram_id
            FROM users
            ORDER BY id ASC
            """
        ).fetchall()
    return [int(row["telegram_id"]) for row in rows if row["telegram_id"]]


def track_event(
    database_path: Path,
    event_name: str,
    telegram_id: int | None = None,
    booking_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    with with_connection(database_path) as conn:
        conn.execute(
            """
            INSERT INTO analytics_events(event_name, telegram_id, booking_id, payload)
            VALUES (?, ?, ?, ?)
            """,
            (
                event_name,
                telegram_id,
                booking_id,
                json.dumps(payload, ensure_ascii=False) if payload else None,
            ),
        )


def get_funnel_stats(database_path: Path, days: int = 30) -> dict[str, int | float]:
    events = ("start", "booking_started", "booking_confirmed", "booking_contacted")
    with with_connection(database_path) as conn:
        rows = conn.execute(
            """
            SELECT event_name, COUNT(*) AS event_count
            FROM analytics_events
            WHERE event_name IN ('start', 'booking_started', 'booking_confirmed', 'booking_contacted')
              AND created_at >= DATETIME(CURRENT_TIMESTAMP, ?)
            GROUP BY event_name
            """,
            (f"-{days} days",),
        ).fetchall()
    stats = {event: 0 for event in events}
    for row in rows:
        stats[str(row["event_name"])] = int(row["event_count"])

    start_count = stats["start"]
    booking_started = stats["booking_started"]
    booking_confirmed = stats["booking_confirmed"]
    booking_contacted = stats["booking_contacted"]

    return {
        **stats,
        "start_to_booking_started": round((booking_started / start_count) * 100, 1) if start_count else 0.0,
        "booking_started_to_confirmed": round((booking_confirmed / booking_started) * 100, 1)
        if booking_started
        else 0.0,
        "confirmed_to_contacted": round((booking_contacted / booking_confirmed) * 100, 1)
        if booking_confirmed
        else 0.0,
    }


def upsert_booking_session(
    database_path: Path,
    telegram_id: int,
    state: str,
    payload: dict[str, Any],
) -> None:
    with with_connection(database_path) as conn:
        conn.execute(
            """
            INSERT INTO booking_sessions(telegram_id, state, payload, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(telegram_id) DO UPDATE SET
                state=excluded.state,
                payload=excluded.payload,
                updated_at=CURRENT_TIMESTAMP
            """,
            (telegram_id, state, json.dumps(payload, ensure_ascii=False)),
        )


def get_booking_session(database_path: Path, telegram_id: int, max_age_hours: int = 24) -> dict[str, Any] | None:
    with with_connection(database_path) as conn:
        row = conn.execute(
            """
            SELECT state, payload, updated_at
            FROM booking_sessions
            WHERE telegram_id = ?
              AND updated_at >= DATETIME(CURRENT_TIMESTAMP, ?)
            """,
            (telegram_id, f"-{max_age_hours} hours"),
        ).fetchone()
    if not row:
        return None
    return {"state": str(row["state"]), "payload": json.loads(row["payload"])}


def clear_booking_session(database_path: Path, telegram_id: int) -> None:
    with with_connection(database_path) as conn:
        conn.execute(
            "DELETE FROM booking_sessions WHERE telegram_id = ?",
            (telegram_id,),
        )


def has_user_trial_history(database_path: Path, telegram_id: int) -> bool:
    with with_connection(database_path) as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM bookings b
            JOIN users u ON u.id = b.user_id
            WHERE u.telegram_id = ?
              AND b.status IN ('pending', 'contacted')
            LIMIT 1
            """,
            (telegram_id,),
        ).fetchone()
    return bool(row)


def get_latest_user_booking(database_path: Path, telegram_id: int) -> Row | None:
    with with_connection(database_path) as conn:
        row = conn.execute(
            """
            SELECT b.id, b.gym_location, b.status, b.created_at
            FROM bookings b
            JOIN users u ON u.id = b.user_id
            WHERE u.telegram_id = ?
            ORDER BY b.id DESC
            LIMIT 1
            """,
            (telegram_id,),
        ).fetchone()
    return row


def bootstrap_admins(database_path: Path, owner_id: int, admin_ids: tuple[int, ...]) -> None:
    if not owner_id and not admin_ids:
        return
    seed_ids = set(admin_ids)
    if owner_id:
        seed_ids.add(owner_id)
    with with_connection(database_path) as conn:
        for telegram_id in seed_ids:
            conn.execute(
                """
                INSERT INTO bot_admins(telegram_id, added_by, status)
                VALUES(?, ?, 'active')
                ON CONFLICT(telegram_id) DO UPDATE SET
                    status='active',
                    updated_at=CURRENT_TIMESTAMP
                """,
                (telegram_id, owner_id or telegram_id),
            )


def is_admin_user(database_path: Path, telegram_id: int) -> bool:
    with with_connection(database_path) as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM bot_admins
            WHERE telegram_id = ? AND status = 'active'
            LIMIT 1
            """,
            (telegram_id,),
        ).fetchone()
    return bool(row)


def get_active_admins(database_path: Path) -> list[Row]:
    with with_connection(database_path) as conn:
        rows = conn.execute(
            """
            SELECT
                a.telegram_id,
                COALESCE(u.username, a.username) AS username,
                a.created_at
            FROM bot_admins a
            LEFT JOIN users u ON u.telegram_id = a.telegram_id
            WHERE a.status = 'active'
            ORDER BY a.created_at ASC
            """
        ).fetchall()
    return rows


def get_active_admin_ids(database_path: Path) -> tuple[int, ...]:
    rows = get_active_admins(database_path)
    return tuple(int(row["telegram_id"]) for row in rows)


def add_admin(
    database_path: Path,
    telegram_id: int,
    username: str | None,
    owner_id: int,
) -> None:
    with with_connection(database_path) as conn:
        conn.execute(
            """
            INSERT INTO bot_admins(telegram_id, username, added_by, status)
            VALUES(?, ?, ?, 'active')
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=COALESCE(excluded.username, bot_admins.username),
                status='active',
                updated_at=CURRENT_TIMESTAMP
            """,
            (telegram_id, username, owner_id),
        )


def remove_admin(database_path: Path, telegram_id: int) -> bool:
    with with_connection(database_path) as conn:
        cursor = conn.execute(
            """
            UPDATE bot_admins
            SET status='removed', updated_at=CURRENT_TIMESTAMP
            WHERE telegram_id = ? AND status = 'active'
            """,
            (telegram_id,),
        )
    return cursor.rowcount > 0


def create_admin_invite(database_path: Path, owner_id: int, ttl_minutes: int = 5) -> tuple[str, Row]:
    token = secrets.token_urlsafe(18)
    with with_connection(database_path) as conn:
        conn.execute(
            """
            INSERT INTO admin_invites(token, created_by, status, expires_at)
            VALUES(?, ?, 'active', DATETIME(CURRENT_TIMESTAMP, ?))
            """,
            (token, owner_id, f"+{ttl_minutes} minutes"),
        )
        row = conn.execute(
            """
            SELECT token, status, created_at, expires_at
            FROM admin_invites
            WHERE token = ?
            """,
            (token,),
        ).fetchone()
    return token, row


def mark_expired_admin_invites(database_path: Path) -> int:
    with with_connection(database_path) as conn:
        cursor = conn.execute(
            """
            UPDATE admin_invites
            SET status='expired'
            WHERE status='active' AND expires_at <= CURRENT_TIMESTAMP
            """
        )
    return cursor.rowcount


def get_admin_invite(database_path: Path, token: str) -> Row | None:
    mark_expired_admin_invites(database_path)
    with with_connection(database_path) as conn:
        row = conn.execute(
            """
            SELECT id, token, status, created_by, created_at, expires_at, used_by, used_at
            FROM admin_invites
            WHERE token = ?
            LIMIT 1
            """,
            (token,),
        ).fetchone()
    return row


def consume_admin_invite(database_path: Path, token: str, used_by: int) -> bool:
    mark_expired_admin_invites(database_path)
    with with_connection(database_path) as conn:
        cursor = conn.execute(
            """
            UPDATE admin_invites
            SET status='used', used_by=?, used_at=CURRENT_TIMESTAMP
            WHERE token = ?
              AND status='active'
              AND expires_at > CURRENT_TIMESTAMP
            """,
            (used_by, token),
        )
    return cursor.rowcount > 0
